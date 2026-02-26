// worker.js - Aiden's Personal Memory API
// Cloudflare Workers + D1 + Vectorize

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS 预检
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Authorization, Content-Type'
        }
      });
    }

    // 公开路由 - 可视化界面（不需要认证）
    if (path === '/viz' || path === '/viz/') {
      return handleVisualization(env);
    }
    
    // 公开路由 - 只读数据接口（用于可视化）
    if (path === '/viz/data' && request.method === 'GET') {
      return await handleVizData(url, env, ctx);
    }

    // Bearer Auth
    const authHeader = request.headers.get('Authorization');
    if (authHeader !== `Bearer ${env.API_KEY}`) {
      return jsonResponse({ error: 'Unauthorized' }, 401);
    }

    try {
      // 路由
      if (path === '/memory' && request.method === 'POST') {
        return await handleWrite(request, env);
      }
      if (path === '/memory/search' && request.method === 'GET') {
        return await handleSearch(url, env, ctx);
      }
      if (path.startsWith('/memory/') && request.method === 'DELETE') {
        const id = path.split('/')[2];
        return await handleDelete(id, env);
      }
      if (path === '/memory/stats' && request.method === 'GET') {
        return await handleStats(env);
      }

      return jsonResponse({ error: 'Not Found' }, 404);
    } catch (err) {
      console.error('Error:', err);
      return jsonResponse({ error: err.message }, 500);
    }
  }
};

// 写入记忆
async function handleWrite(request, env) {
  const { items } = await request.json();
  const url = new URL(request.url);
  const type = url.searchParams.get('type') || 'personal'; // personal|assistant|project

  if (!items || !items.length) {
    return jsonResponse({ error: 'Empty items' }, 400);
  }

  if (items.length > 20) {
    return jsonResponse({ error: 'Max 20 items per request' }, 400);
  }

  // 1. 批量获取 Embedding
  const texts = items.map(i => i.text);
  const embeddings = await getEmbeddings(texts, env);

  const now = Math.floor(Date.now() / 1000);
  const results = [];
  const vectorInserts = [];

  // 2. 准备 D1 批量写入 (新增 type 字段)
  const stmt = env.DB.prepare(`
    INSERT INTO memories (id, text, source, created, accessed, weight, tags, type)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const batch = items.map((item, i) => {
    const id = crypto.randomUUID();
    const weight = item.weight || 1.0;
    const tags = item.tags || [];
    const itemType = item.type || type; // item级别type优先

    results.push({ id, text: item.text, type: itemType });
    vectorInserts.push({
      id,
      values: embeddings[i],
      metadata: { weight, type: itemType }
    });

    return stmt.bind(
      id,
      item.text,
      item.source || 'ai',
      now,
      now,
      weight,
      JSON.stringify(tags),
      itemType
    );
  });

  // 3. 执行写入
  await env.DB.batch(batch);
  await env.VECTORIZE.insert(vectorInserts);

  return jsonResponse({ ok: true, inserted: results });
}

// 检索记忆
async function handleSearch(url, env, ctx) {
  const query = url.searchParams.get('q');
  const limit = Math.min(parseInt(url.searchParams.get('limit') || '5'), 20);
  const type = url.searchParams.get('type') || 'all'; // all|personal|assistant|project
  const format = url.searchParams.get('format') || 'full'; // full|compact|text

  if (!query) {
    return jsonResponse({ error: 'Missing query parameter: q' }, 400);
  }

  // 1. Query 转 Embedding
  const [queryEmbedding] = await getEmbeddings([query], env);

  // 2. 向量搜索（多取一些用于重排）
  const vectorResults = await env.VECTORIZE.query(queryEmbedding, {
    topK: limit * 3,
    returnMetadata: true
  });

  if (!vectorResults.matches?.length) {
    return jsonResponse({ results: [] });
  }

  // 3. 从 D1 获取完整数据
  const ids = vectorResults.matches.map(m => m.id);
  const placeholders = ids.map(() => '?').join(',');
  
  let sql = `SELECT * FROM memories WHERE id IN (${placeholders})`;
  if (type !== 'all') {
    sql += ` AND type = ?`;
  }
  
  const stmt = env.DB.prepare(sql);
  const bindings = type !== 'all' ? [...ids, type] : [...ids];
  const rows = await stmt.bind(...bindings).all();

  // 4. 计算最终分数（优化后的混合权重模型）
  const now = Math.floor(Date.now() / 1000);
  const MIN_SCORE_THRESHOLD = 0.20;  // 最低得分阈值
  const MAX_PER_SOURCE = 3;          // 每来源最多返回数
  
  // 第一阶段：计算基础分数
  let results = rows.results
    .map(row => {
      const match = vectorResults.matches.find(m => m.id === row.id);
      const similarity = match?.score || 0;
      
      // 跳过低相似度的结果
      if (similarity < 0.15) {
        return null;
      }
      
      const base = row.weight || 1.0;
      
      // 优化 recency: 使用指数衰减，7天内保持高权重
      const daysSinceAccessed = (now - row.accessed) / 86400;
      const recency = Math.exp(-daysSinceAccessed / 30) * 0.5 + 0.5; // 0.5-1.0范围
      
      // 优化 frequency: 给新内容基础分0.3，避免完全失效
      const accessCount = row.access_count || 0;
      const frequency = accessCount === 0 ? 0.3 : Math.min(Math.log(accessCount + 1) / Math.log(10), 1.0);
      
      // 内容质量评分（基于文本结构）
      let qualityScore = 0.5;
      const text = row.text || '';
      const textLen = text.length;
      // 长度适中加分
      if (textLen >= 300 && textLen <= 1500) qualityScore += 0.2;
      else if (textLen >= 150) qualityScore += 0.1;
      // 有结构加分
      if (text.includes('#')) qualityScore += 0.1;  // 有标题
      if (text.includes('```')) qualityScore += 0.1; // 有代码
      
      // 新的权重公式：similarity占50%，其他因子占50%
      const mixedWeight = 0.4 * base + 0.2 * recency + 0.2 * frequency + 0.2 * qualityScore;
      const finalScore = similarity * 0.5 + mixedWeight * 0.5;
      
      return {
        id: row.id,
        text: row.text,
        score: parseFloat(finalScore.toFixed(4)),
        similarity: parseFloat(similarity.toFixed(4)),
        weight: row.weight,
        source: row.source || 'unknown',
        _debug: {
          base: parseFloat(base.toFixed(3)),
          recency: parseFloat(recency.toFixed(3)),
          frequency: parseFloat(frequency.toFixed(3)),
          quality: parseFloat(qualityScore.toFixed(3)),
          mixedWeight: parseFloat(mixedWeight.toFixed(3)),
          accessCount,
          daysSinceAccessed: Math.round(daysSinceAccessed)
        },
        tags: JSON.parse(row.tags || '[]'),
        type: row.type || 'personal',
        created: row.created
      };
    })
    .filter(r => r !== null && r.score >= MIN_SCORE_THRESHOLD);
  
  // 第二阶段：来源多样性处理（MMR-like算法）
  const sourceCounts = {};
  const diverseResults = [];
  
  for (const result of results) {
    const source = result.source;
    if (!sourceCounts[source]) sourceCounts[source] = 0;
    
    if (sourceCounts[source] < MAX_PER_SOURCE) {
      diverseResults.push(result);
      sourceCounts[source]++;
    }
    
    if (diverseResults.length >= limit * 2) break;
  }
  
  // 第三阶段：最终排序和截取
  results = diverseResults
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);

  // 5. 异步更新访问时间和访问次数（不阻塞响应）
  ctx.waitUntil(updateAccessStats(results.map(r => r.id), env));

  // 6. 根据format参数返回不同格式
  if (format === 'text') {
    // 纯文本模式 - 最省token
    const text = results.map(r => r.text).join('\n---\n');
    return new Response(text, {
      headers: { 'Content-Type': 'text/plain; charset=utf-8' }
    });
  }
  
  if (format === 'compact') {
    // 紧凑模式 - 只返回必要字段
    return jsonResponse({
      results: results.map(r => ({
        text: r.text,
        score: r.score
      }))
    });
  }
  
  // full模式 - 完整返回（默认）
  return jsonResponse({ results });
}

// 删除记忆
async function handleDelete(id, env) {
  if (!id) {
    return jsonResponse({ error: 'Missing id' }, 400);
  }

  // 先检查是否存在
  const existing = await env.DB
    .prepare('SELECT id FROM memories WHERE id = ?')
    .bind(id)
    .first();

  if (!existing) {
    return jsonResponse({ error: 'Not found' }, 404);
  }

  await env.DB.prepare('DELETE FROM memories WHERE id = ?').bind(id).run();
  await env.VECTORIZE.deleteByIds([id]);

  return jsonResponse({ ok: true, deleted: id });
}

// 统计信息
async function handleStats(env) {
  const countResult = await env.DB
    .prepare('SELECT COUNT(*) as count FROM memories')
    .first();

  const recentResult = await env.DB
    .prepare('SELECT * FROM memories ORDER BY created DESC LIMIT 5')
    .all();

  return jsonResponse({
    total: countResult.count,
    recent: recentResult.results.map(r => ({
      id: r.id,
      text: r.text.slice(0, 50) + (r.text.length > 50 ? '...' : ''),
      created: r.created
    }))
  });
}

// 批量获取 Embedding
async function getEmbeddings(texts, env) {
  const response = await fetch('https://api.openai.com/v1/embeddings', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.OPENAI_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: 'text-embedding-3-small',
      input: texts
    })
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`OpenAI API error: ${error}`);
  }

  const data = await response.json();
  return data.data.map(d => d.embedding);
}

// 异步更新访问时间
async function updateAccessTime(ids, env) {
  const now = Math.floor(Date.now() / 1000);
  const stmt = env.DB.prepare('UPDATE memories SET accessed = ? WHERE id = ?');
  await env.DB.batch(ids.map(id => stmt.bind(now, id)));
}

// 异步更新访问时间和访问次数（混合权重模型用）
async function updateAccessStats(ids, env) {
  const now = Math.floor(Date.now() / 1000);
  const stmt = env.DB.prepare(`
    UPDATE memories 
    SET accessed = ?, access_count = COALESCE(access_count, 0) + 1 
    WHERE id = ?
  `);
  await env.DB.batch(ids.map(id => stmt.bind(now, id)));
}

// 统一响应格式
function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*'
    }
  });
}

// 可视化专用数据接口（公开只读）
async function handleVizData(url, env, ctx) {
  try {
    const query = url.searchParams.get('q') || '';
    const limit = Math.min(parseInt(url.searchParams.get('limit') || '100'), 200);
    
    // 1. 获取统计
    const countResult = await env.DB.prepare('SELECT COUNT(*) as count FROM memories').first();
    
    // 2. 按类型统计
    const typeStats = await env.DB.prepare(`
      SELECT type, COUNT(*) as count 
      FROM memories 
      GROUP BY type
    `).all();
    
    // 3. 获取记忆数据
    let memories = [];
    
    if (query && query.length > 0) {
      // 有搜索词：使用语义搜索
      const [queryEmbedding] = await getEmbeddings([query], env);
      const vectorResults = await env.VECTORIZE.query(queryEmbedding, {
        topK: limit,
        returnMetadata: true
      });
      
      if (vectorResults.matches?.length) {
        const ids = vectorResults.matches.map(m => m.id);
        const placeholders = ids.map(() => '?').join(',');
        const rows = await env.DB.prepare(`
          SELECT * FROM memories WHERE id IN (${placeholders})
        `).bind(...ids).all();
        
        memories = rows.results.map(row => {
          const match = vectorResults.matches.find(m => m.id === row.id);
          const similarity = match?.score || 0;
          return {
            id: row.id,
            text: row.text,
            score: parseFloat((similarity * row.weight).toFixed(4)),
            similarity: parseFloat(similarity.toFixed(4)),
            weight: row.weight,
            type: row.type || 'personal',
            created: row.created
          };
        }).sort((a, b) => b.score - a.score);
      }
    } else {
      // 无搜索词：直接按时间返回最近的
      const rows = await env.DB.prepare(`
        SELECT * FROM memories 
        ORDER BY created DESC 
        LIMIT ?
      `).bind(limit).all();
      
      memories = rows.results.map(row => ({
        id: row.id,
        text: row.text,
        score: row.weight,
        similarity: 0,
        weight: row.weight,
        type: row.type || 'personal',
        created: row.created
      }));
    }
    
    return jsonResponse({
      total: countResult.count,
      typeStats: typeStats.results,
      memories
    });
  } catch (err) {
    console.error('handleVizData error:', err);
    return jsonResponse({ 
      error: err.message,
      stack: err.stack 
    }, 500);
  }
}

// 可视化页面（公开访问）
function handleVisualization(env) {
  const html = `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw Memory Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: #0f0f23; 
            color: #e4e4e7;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { 
            font-size: 2.5em; 
            margin-bottom: 10px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stats { 
            display: flex; 
            gap: 20px; 
            margin: 30px 0;
            flex-wrap: wrap;
        }
        .stat-card { 
            background: #18181b; 
            padding: 20px; 
            border-radius: 12px; 
            flex: 1; 
            min-width: 200px;
            border: 1px solid #27272a;
        }
        .stat-value { 
            font-size: 2.5em; 
            font-weight: bold; 
            color: #667eea; 
        }
        .stat-label { 
            color: #a1a1aa; 
            margin-top: 5px; 
        }
        .charts { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
            margin: 30px 0;
        }
        .chart-container { 
            background: #18181b; 
            padding: 20px; 
            border-radius: 12px;
            border: 1px solid #27272a;
        }
        @media (max-width: 768px) {
            .charts { grid-template-columns: 1fr; }
        }
        .memory-list { margin-top: 30px; }
        .memory-item { 
            background: #18181b; 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 8px;
            border-left: 3px solid #667eea;
            border: 1px solid #27272a;
            transition: transform 0.2s;
        }
        .memory-item:hover {
            transform: translateX(5px);
            border-left-color: #764ba2;
        }
        .memory-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .memory-type { 
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }
        .type-personal { background: #1e3a8a; color: #93c5fd; }
        .type-assistant { background: #134e4a; color: #5eead4; }
        .type-project { background: #7c2d12; color: #fdba74; }
        .type-other { background: #3f3f46; color: #d4d4d8; }
        .memory-score { 
            color: #a1a1aa; 
            font-size: 0.9em;
        }
        .memory-text { 
            line-height: 1.6; 
            color: #e4e4e7;
        }
        .memory-meta {
            margin-top: 8px;
            font-size: 0.85em;
            color: #71717a;
        }
        .loading { text-align: center; padding: 40px; color: #a1a1aa; }
        .error { 
            background: #450a0a; 
            color: #fca5a5; 
            padding: 15px; 
            border-radius: 8px; 
            margin: 20px 0;
            border: 1px solid #7f1d1d;
        }
        .search-box {
            margin: 20px 0;
            display: flex;
            gap: 10px;
        }
        .search-box input {
            flex: 1;
            padding: 12px;
            border: 1px solid #27272a;
            border-radius: 8px;
            background: #18181b;
            color: #e4e4e7;
            font-size: 1em;
        }
        .search-box button {
            padding: 12px 24px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.2s;
        }
        .search-box button:hover {
            background: #764ba2;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 OpenClaw Memory</h1>
        <p style="color: #a1a1aa; margin-bottom: 20px;">Aiden's Personal Memory Visualization</p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="totalCount">-</div>
                <div class="stat-label">Total Memories</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="personalCount">-</div>
                <div class="stat-label">Personal</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="assistantCount">-</div>
                <div class="stat-label">Assistant</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="projectCount">-</div>
                <div class="stat-label">Project</div>
            </div>
        </div>

        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Search memories..." />
            <button onclick="searchMemories()">Search</button>
        </div>
        
        <div class="charts">
            <div class="chart-container">
                <canvas id="typeChart"></canvas>
            </div>
            <div class="chart-container">
                <canvas id="timeChart"></canvas>
            </div>
        </div>
        
        <div class="memory-list">
            <h2 style="margin-bottom: 15px;">Recent Memories</h2>
            <div id="memoryList" class="loading">Loading...</div>
        </div>
    </div>
    
    <script>
        let allMemories = [];
        
        async function loadMemories() {
            try {
                // 使用公开接口获取数据（不带搜索词，返回最近记录）
                console.log('Fetching data from /viz/data...');
                const res = await fetch('/viz/data?limit=100');
                console.log('Response status:', res.status);
                
                if (!res.ok) {
                    const text = await res.text();
                    console.error('Response error:', text);
                    throw new Error('Failed to fetch data: ' + res.status);
                }
                
                const data = await res.json();
                console.log('Data loaded:', data);
                
                if (data.error) {
                    throw new Error(data.error);
                }
                
                allMemories = data.memories || [];
                
                // 更新统计
                const typeCounts = {};
                (data.typeStats || []).forEach(stat => {
                    typeCounts[stat.type] = stat.count;
                });
                
                document.getElementById('totalCount').textContent = data.total || 0;
                document.getElementById('personalCount').textContent = typeCounts.personal || 0;
                document.getElementById('assistantCount').textContent = typeCounts.assistant || 0;
                document.getElementById('projectCount').textContent = typeCounts.project || 0;
                
                // 渲染图表
                renderCharts(allMemories);
                
                // 渲染记忆列表
                renderMemories(allMemories);
                
            } catch (err) {
                console.error('Load error:', err);
                document.getElementById('memoryList').innerHTML = 
                    '<div class="error">Error loading memories: ' + err.message + '<br/>Check browser console for details.</div>';
            }
        }
        
        function renderCharts(memories) {
            // 类型分布饼图
            const typeCounts = memories.reduce((acc, m) => {
                acc[m.type] = (acc[m.type] || 0) + 1;
                return acc;
            }, {});
            
            new Chart(document.getElementById('typeChart'), {
                type: 'doughnut',
                data: {
                    labels: Object.keys(typeCounts),
                    datasets: [{
                        data: Object.values(typeCounts),
                        backgroundColor: ['#3b82f6', '#14b8a6', '#f97316', '#71717a']
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { labels: { color: '#e4e4e7' } },
                        title: { 
                            display: true, 
                            text: 'Memory Type Distribution',
                            color: '#e4e4e7',
                            font: { size: 16 }
                        }
                    }
                }
            });
            
            // 时间趋势图（最近30天）
            const now = Math.floor(Date.now() / 1000);
            const daySeconds = 86400;
            const days = Array.from({length: 30}, (_, i) => now - (29-i) * daySeconds);
            const dayCounts = days.map(day => {
                return memories.filter(m => 
                    m.created >= day && m.created < day + daySeconds
                ).length;
            });
            
            new Chart(document.getElementById('timeChart'), {
                type: 'line',
                data: {
                    labels: days.map(d => new Date(d * 1000).toLocaleDateString('en-US', {month: 'short', day: 'numeric'})),
                    datasets: [{
                        label: 'Memories Created',
                        data: dayCounts,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { labels: { color: '#e4e4e7' } },
                        title: { 
                            display: true, 
                            text: 'Memory Creation Timeline (30d)',
                            color: '#e4e4e7',
                            font: { size: 16 }
                        }
                    },
                    scales: {
                        x: { ticks: { color: '#a1a1aa' }, grid: { color: '#27272a' } },
                        y: { ticks: { color: '#a1a1aa' }, grid: { color: '#27272a' } }
                    }
                }
            });
        }
        
        function renderMemories(memories) {
            const listContainer = document.getElementById('memoryList');
            if (!memories.length) {
                listContainer.innerHTML = '<div class="loading">No memories found</div>';
                return;
            }
            
            listContainer.innerHTML = memories.map(mem => {
                const date = new Date(mem.created * 1000).toLocaleString('zh-CN');
                return \`
                    <div class="memory-item">
                        <div class="memory-header">
                            <span class="memory-type type-\${mem.type}">\${mem.type}</span>
                            <span class="memory-score">Score: \${mem.score.toFixed(3)}</span>
                        </div>
                        <div class="memory-text">\${mem.text}</div>
                        <div class="memory-meta">
                            📅 \${date} • ⚖️ Weight: \${mem.weight} • 🎯 Similarity: \${mem.similarity.toFixed(3)}
                        </div>
                    </div>
                \`;
            }).join('');
        }
        
        async function searchMemories() {
            const query = document.getElementById('searchInput').value.trim();
            if (!query) {
                renderMemories(allMemories);
                return;
            }
            
            document.getElementById('memoryList').innerHTML = '<div class="loading">Searching...</div>';
            
            try {
                const res = await fetch('/viz/data?q=' + encodeURIComponent(query) + '&limit=50');
                if (!res.ok) throw new Error('Search failed');
                const data = await res.json();
                renderMemories(data.memories || []);
            } catch (err) {
                document.getElementById('memoryList').innerHTML = 
                    '<div class="error">Search error: ' + err.message + '</div>';
            }
        }
        
        // 回车搜索
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchMemories();
        });
        
        // 初始加载
        loadMemories();
    </script>
</body>
</html>`;

  return new Response(html, {
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-cache'
    }
  });
}
