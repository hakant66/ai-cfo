$body = @{
  email = "system@yourco.com"
  password = "<system-user-password>"
  company_id = 6
} | ConvertTo-Json

$resp = Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/auth/login" `
  -ContentType "application/json" `
  -Body $body

$resp.access_token
