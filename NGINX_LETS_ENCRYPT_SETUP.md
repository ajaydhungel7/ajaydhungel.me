# Nginx + Certbot + Let's Encrypt Setup

Alternative to Caddy if you prefer Nginx.

## Step-by-Step Setup

### 1. Launch EC2 Instance
- Ubuntu 22.04 LTS
- t3.micro is sufficient
- Security group: Allow 80, 443, 22

### 2. Install Nginx and Certbot

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 3. Configure Nginx

Edit `/etc/nginx/sites-available/ajaydhungel.blog`:

```nginx
server {
    listen 80;
    server_name ajaydhungel.blog;

    location / {
        proxy_pass http://ajaydhungel.me.s3-website-us-east-1.amazonaws.com;
        proxy_set_header Host ajaydhungel.me.s3-website-us-east-1.amazonaws.com;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/ajaydhungel.blog /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Get Let's Encrypt Certificate

```bash
sudo certbot --nginx -d ajaydhungel.blog
```

Certbot will:
- Get Let's Encrypt certificate
- Modify Nginx config automatically
- Set up auto-renewal

### 5. Verify Auto-Renewal

```bash
sudo certbot renew --dry-run
```

### 6. Update DNS

Point your domain to EC2's Elastic IP (recommended) or public IP.

## Auto-Renewal

Certbot sets up a systemd timer automatically. Verify:

```bash
sudo systemctl status certbot.timer
```

## Cost

Same as Caddy setup: ~$7-15/month
