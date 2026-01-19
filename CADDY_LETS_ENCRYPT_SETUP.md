# Caddy + Let's Encrypt Setup (No CloudFront/Cloudflare)

This setup uses Caddy on EC2 to provide HTTPS with Let's Encrypt while keeping your S3 bucket as-is.

## Architecture

```
User → HTTPS (Let's Encrypt) → Caddy on EC2 → HTTP → S3 Bucket
```

## Prerequisites

- AWS EC2 instance (t3.micro is fine, ~$5-10/month)
- Domain DNS access
- SSH access to EC2

## Step-by-Step Setup

### 1. Launch EC2 Instance

```bash
# Launch a t3.micro instance
# - Ubuntu 22.04 LTS
# - Security group: Allow HTTP (80), HTTPS (443), SSH (22)
# - Create/use key pair for SSH
```

### 2. Install Caddy

SSH into your EC2 instance:

```bash
sudo apt update
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

### 3. Configure Caddy

Create/edit `/etc/caddy/Caddyfile`:

```caddy
ajaydhungel.blog {
    reverse_proxy ajaydhungel.me.s3-website-us-east-1.amazonaws.com {
        header_up Host ajaydhungel.me.s3-website-us-east-1.amazonaws.com
    }
}
```

**What this does:**
- Caddy automatically gets Let's Encrypt certificate for `ajaydhungel.blog`
- Proxies all requests to your S3 website endpoint
- Handles SSL termination

### 4. Start Caddy

```bash
sudo systemctl enable caddy
sudo systemctl start caddy
sudo systemctl status caddy
```

### 5. Update DNS

In your domain registrar (Spaceship):
- Change CNAME from S3 to your EC2 instance's public IP or Elastic IP
- Or use an A record pointing to the IP

**Better option - Use Elastic IP:**
```bash
# In AWS Console: EC2 → Elastic IPs → Allocate
# Associate with your EC2 instance
# Use this IP in DNS A record
```

### 6. Verify

```bash
# Check Caddy logs
sudo journalctl -u caddy -f

# Test HTTPS
curl -I https://ajaydhungel.blog
```

## Caddyfile Explained

```caddy
ajaydhungel.blog {                    # Your domain
    reverse_proxy                      # Proxy requests
        ajaydhungel.me.s3-website...   # To S3 endpoint
    {
        header_up Host ...              # Preserve host header
    }
}
```

Caddy automatically:
- ✅ Gets Let's Encrypt certificate
- ✅ Auto-renews certificates
- ✅ Handles HTTP → HTTPS redirect
- ✅ Proxies to S3

## Security Group Rules

Make sure your EC2 security group allows:
- **Inbound:**
  - Port 80 (HTTP) - from 0.0.0.0/0
  - Port 443 (HTTPS) - from 0.0.0.0/0
  - Port 22 (SSH) - from your IP only

## Cost Estimate

- **EC2 t3.micro**: ~$7-10/month
- **Data transfer**: ~$0.09/GB (first 1GB free)
- **Let's Encrypt**: Free
- **Total**: ~$7-15/month depending on traffic

## Maintenance

Caddy handles everything automatically:
- ✅ Certificate renewal (automatic)
- ✅ No manual intervention needed

## Troubleshooting

### Check Caddy status
```bash
sudo systemctl status caddy
sudo journalctl -u caddy -n 50
```

### Test configuration
```bash
sudo caddy validate --config /etc/caddy/Caddyfile
```

### Reload Caddy
```bash
sudo systemctl reload caddy
```

## Alternative: Nginx + Certbot

If you prefer Nginx:

1. Install Nginx and Certbot
2. Configure Nginx to proxy to S3
3. Run `certbot --nginx -d ajaydhungel.blog`
4. Set up auto-renewal cron job

Caddy is simpler because it handles Let's Encrypt automatically!
