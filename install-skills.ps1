# Skill 安装脚本 - 分层加载方案
$sourceDir = "C:\Users\sdses\Desktop\神思\ai孪生\agentp平台skill\skill"
$libraryDir = "$env:USERPROFILE\.kimi\skill-library"
$activeDir = "$env:USERPROFILE\.kimi\skills-active"

# 创建目录
New-Item -ItemType Directory -Path $libraryDir -Force | Out-Null
New-Item -ItemType Directory -Path $activeDir -Force | Out-Null

# 分类函数
function Get-SkillCategory($skillName) {
    if ($skillName -match '(bash|git|docker|makefile|changelog|commit|readme|version|dotenv|ssh|nginx|jenkins|gitlab|github-action|yaml|json|npm|package|pre-commit|release|environment|branch|linux|dockerfile|docker-compose|container|gitignore)') { return '01-devops-basics' }
    if ($skillName -match '(terraform|ansible|kubernetes|k8s|helm|prometheus|grafana|alertmanager|istio|envoy|argocd|flux|vault|consul|elasticsearch)') { return '02-devops-advanced' }
    if ($skillName -match '(security|secret|password|jwt|oauth|csrf|cors|xss|sql-injection|certificate|https|encryption|scan|vulnerability|dependency)') { return '03-security-fundamentals' }
    if ($skillName -match '(gdpr|hipaa|pci-dss|soc2|iso27001|penetration|threat|waf|siem|forensics|attack|zero-trust|iam|rbac)') { return '04-security-advanced' }
    if ($skillName -match '(react|vue|angular|frontend|css|tailwind|webpack|vite|eslint|typescript|javascript|component|hook|composable|store|redux|pwa|web-vitals|lighthouse|accessibility|seo|responsive|animation|canvas|svg)') { return '05-frontend-dev' }
    if ($skillName -match '(backend|api|rest|graphql|grpc|websocket|server|middleware|router|controller|service|orm|cache|redis|auth|sql|mysql|postgres|mongodb|prisma|django|flask|fastapi|express|nest|spring|java|kotlin|go|gin|rust|php|laravel|ruby|rails|python|node|dotnet|serverless|lambda|kafka|rabbitmq)') { return '06-backend-dev' }
    if ($skillName -match '(ml|machine|learning|training|model|neural|deep|tensorflow|pytorch|sklearn|xgboost|keras|huggingface|transformer|bert|gpt|llm|nlp|cv|vision|classification|regression|clustering|embedding|vector|mlflow|wandb|hyperparameter|fine-tuning|lora)') { return '07-ml-training' }
    if ($skillName -match '(deploy|serving|inference|prediction|batch|streaming|torchserve|triton|onnx|tflite|edge|canary|blue-green|model|registry|drift|monitoring|evidently)') { return '08-ml-deployment' }
    if ($skillName -match '(test|testing|automation|e2e|integration|unit|jest|mocha|vitest|pytest|junit|cucumber|cypress|playwright|puppeteer|selenium|mock|snapshot)') { return '09-test-automation' }
    if ($skillName -match '(performance|load|stress|k6|locust|gatling|jmeter|artillery|profiling|tracing|opentelemetry|jaeger|zipkin)') { return '10-performance-testing' }
    if ($skillName -match '(data|pipeline|etl|elt|airflow|prefect|dagster|spark|flink|kafka|streaming|batch|cdc|debezium|logstash|fluentd)') { return '11-data-pipelines' }
    if ($skillName -match '(analytics|bi|report|dashboard|tableau|power-bi|looker|metabase|superset|pandas|numpy|polars|duckdb|bigquery|snowflake|databricks)') { return '12-data-analytics' }
    if ($skillName -match '(aws|amazon|ec2|s3|rds|lambda|dynamodb|vpc|iam|cloudformation|cdk|sam|serverless|api-gateway|cognito|ses|sns|sqs|eventbridge|ecs|fargate|eks|cloudfront|route53|cloudwatch|sagemaker)') { return '13-aws-skills' }
    if ($skillName -match '(gcp|google|cloud|compute|gke|app|run|cloud-functions|cloud-build|bigquery|spanner|cloud-sql|cloud-storage|pub|sub|dataflow|vertex|ai|automl)') { return '14-gcp-skills' }
    if ($skillName -match '(api|rest|graphql|grpc|openapi|swagger|postman|json|schema|protobuf|gqlgen|prisma|apollo|federation|subscriptions|webhooks)') { return '15-api-development' }
    if ($skillName -match '(integration|stripe|firebase|supabase|auth0|okta|sendgrid|twilio|slack|discord|telegram|zoom|shopify|salesforce|hubspot)') { return '16-api-integration' }
    if ($skillName -match '(doc|documentation|markdown|mdx|readme|wiki|confluence|notion|obsidian|docusaurus|vitepress|mkdocs)') { return '17-technical-docs' }
    if ($skillName -match '(visual|design|image|video|animation|svg|canvas|icon|logo|banner|thumbnail|figma|sketch|adobe|blender|three)') { return '18-visual-content' }
    if ($skillName -match '(automation|workflow|rpa|zapier|n8n|robot|process|bot|scraping|crawler|parser|scheduler|cron)') { return '19-business-automation' }
    if ($skillName -match '(enterprise|workflow|bpm|camunda|zeebe|activiti|flowable|orchestration|saga|audit|compliance|governance|risk|legal)') { return '20-enterprise-workflows' }
    if ($skillName -match '-lsp$') { return '91-lsp-tools' }
    if ($skillName -match '(agent|ralph|vivian|serena|mcp|codemod|evolution|evolving|improving|self-|skill-creator|skill-manager|gateway)') { return '92-agent-tools' }
    if ($skillName -match '(productivity|time|task|todo|note|calendar|schedule|meeting|email|chat|collaboration|notion|todoist|trello|asana|linear|jira)') { return '93-productivity' }
    return '90-general'
}

# 获取所有 skill
$skillFolders = Get-ChildItem -Path $sourceDir -Recurse -Filter "SKILL.md" | ForEach-Object { $_.Directory }
Write-Host "找到 $($skillFolders.Count) 个 skill 待安装..."

# 移动并分类
$moved = 0
$categories = @{}

foreach ($folder in $skillFolders) {
    $skillName = $folder.Name
    $category = Get-SkillCategory $skillName
    
    $targetDir = "$libraryDir\$category"
    $targetPath = "$targetDir\$skillName"
    
    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }
    
    if (Test-Path $targetPath) {
        Remove-Item -Path $targetPath -Recurse -Force
    }
    
    Copy-Item -Path $folder.FullName -Destination $targetPath -Recurse -Force
    $moved++
    
    # 记录分类统计
    if (-not $categories.ContainsKey($category)) {
        $categories[$category] = 0
    }
    $categories[$category]++
}

Write-Host "`n安装完成: $moved 个 skill 到 $libraryDir"
Write-Host "`n分类统计:"
$categories.GetEnumerator() | Sort-Object Name | ForEach-Object {
    Write-Host "  $($_.Key): $($_.Value) 个"
}

# 创建 skills-active 目录结构
Write-Host "`n创建激活目录结构..."

# 高频 skill 列表（推荐）
$highFrequencySkills = @(
    'git-workflow-manager',
    'python-project',
    'code-review',
    'dockerfile-generator',
    'code-mentor',
    'debug-agent',
    'skill-creator'
)

# 创建软链接（Windows 用符号链接）
foreach ($skill in $highFrequencySkills) {
    $sourcePath = $null
    # 在各分类中查找
    foreach ($cat in $categories.Keys) {
        $possiblePath = "$libraryDir\$cat\$skill"
        if (Test-Path $possiblePath) {
            $sourcePath = $possiblePath
            break
        }
    }
    
    if ($sourcePath) {
        $linkPath = "$activeDir\$skill"
        if (Test-Path $linkPath) {
            Remove-Item -Path $linkPath -Force
        }
        # Windows 创建 junction（目录软链接）
        cmd /c mklink /J "$linkPath" "$sourcePath" | Out-Null
        Write-Host "  已链接: $skill"
    }
}

Write-Host "`n✅ 完成！使用方法:"
Write-Host "  kimi --skills-dir '$activeDir'"
Write-Host "`n高频 skill 已链接，其余 skill 通过 gateway 按需读取"
