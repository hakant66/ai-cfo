$body = @{
  email = "demo@aicfo.dev"
  password = "<aicfo12345>"
  company_id = 6
} | ConvertTo-Json

$resp = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/auth/login" `
  -ContentType "application/json" `
  -Body $body

$resp.access_token
