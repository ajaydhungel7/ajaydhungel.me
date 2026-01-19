# S3 + Let's Encrypt Architecture

## You Can Keep S3! ✅

You **don't need to move away from S3**. Here's how it works:

## Architecture

```
User → HTTPS (Let's Encrypt) → Proxy/CDN → HTTP → S3 Bucket
```

The proxy/CDN terminates the SSL connection and forwards requests to your S3 bucket over HTTP.

## How It Works

1. **User visits** `https://ajaydhungel.blog`
2. **Proxy/CDN** handles the HTTPS connection (with Let's Encrypt certificate)
3. **Proxy/CDN** forwards request to S3 over HTTP
4. **S3** serves your static files
5. **Response** goes back through proxy/CDN with HTTPS

Your S3 bucket stays exactly as it is - no changes needed!

## Options That Keep S3

### Option 1: CloudFront + ACM (Recommended)
- ✅ Keep S3 as origin
- ✅ Free SSL (ACM, similar to Let's Encrypt)
- ✅ CloudFront proxies to S3
- ✅ No code changes needed

**Setup:**
- CloudFront distribution
- Origin: `ajaydhungel.me.s3-website-us-east-1.amazonaws.com`
- SSL certificate from ACM
- Point DNS to CloudFront

### Option 2: Caddy + EC2
- ✅ Keep S3 as origin
- ✅ Uses Let's Encrypt directly
- ✅ Caddy proxies to S3

**Setup:**
- Small EC2 instance running Caddy
- Caddyfile: `reverse_proxy ajaydhungel.me.s3-website-us-east-1.amazonaws.com`
- Caddy automatically gets Let's Encrypt cert
- Point DNS to EC2 IP

### Option 3: Nginx + Certbot + EC2
- ✅ Keep S3 as origin
- ✅ Uses Let's Encrypt directly
- ✅ Nginx proxies to S3

**Setup:**
- EC2 instance with Nginx
- Certbot for Let's Encrypt
- Nginx config proxies to S3
- Point DNS to EC2 IP

## What Stays the Same

- ✅ Your S3 bucket (`ajaydhungel.me`)
- ✅ Your GitHub Actions deployment
- ✅ Your content structure
- ✅ Everything in your repo

## What Changes

- 🔄 DNS points to proxy/CDN instead of S3 directly
- 🔄 Proxy/CDN handles SSL termination
- ✅ You get HTTPS!

## Recommendation

**Use CloudFront + ACM** - It's the simplest, most reliable, and keeps everything in AWS. ACM certificates are free and auto-renew, just like Let's Encrypt.

## Cost Comparison

- **CloudFront + ACM**: ~$0.085/GB data transfer (first 10TB free/month)
- **Caddy/Nginx on EC2**: ~$5-10/month for t3.micro instance + data transfer

Both keep your S3 bucket exactly as it is!
