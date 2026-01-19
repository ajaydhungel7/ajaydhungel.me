# Let's Encrypt SSL Setup for ajaydhungel.blog

Since S3 website endpoints only support HTTP, you need a proxy/CDN to terminate SSL. Here are options for using Let's Encrypt:

## Option 1: CloudFront + AWS Certificate Manager (Recommended) ⭐

**Why this is best:**
- ACM certificates are free (like Let's Encrypt)
- Fully managed by AWS
- Works seamlessly with CloudFront
- Auto-renewal handled by AWS

**Setup Steps:**

1. **Request Certificate in ACM:**
   ```bash
   # Or use AWS Console: Certificate Manager → Request Certificate
   aws acm request-certificate \
     --domain-name ajaydhungel.blog \
     --validation-method DNS \
     --region us-east-1
   ```

2. **Validate Domain:**
   - ACM will provide DNS validation records
   - Add CNAME records to your DNS provider
   - Wait for validation (usually 5-30 minutes)

3. **Create CloudFront Distribution:**
   - Origin: `ajaydhungel.me.s3-website-us-east-1.amazonaws.com`
   - Origin Protocol: HTTP only
   - Alternate Domain Names: `ajaydhungel.blog`
   - SSL Certificate: Select your ACM certificate
   - Viewer Protocol Policy: Redirect HTTP to HTTPS

4. **Update DNS:**
   - Change CNAME from S3 to CloudFront distribution domain

## Option 2: Caddy Server (Reverse Proxy)

**Pros:**
- Automatic Let's Encrypt certificates
- Auto-renewal
- Simple configuration

**Setup:**
1. Deploy Caddy on EC2 or Lambda
2. Configure Caddyfile:
   ```
   ajaydhungel.blog {
       reverse_proxy ajaydhungel.me.s3-website-us-east-1.amazonaws.com
   }
   ```
3. Caddy automatically gets Let's Encrypt certificate

## Option 3: Nginx + Certbot

**Pros:**
- Full control
- Uses Let's Encrypt directly

**Cons:**
- More complex setup
- Need to manage EC2 instance
- Manual renewal (or cron job)

**Setup:**
1. Deploy Nginx on EC2
2. Install Certbot: `sudo apt install certbot python3-certbot-nginx`
3. Get certificate: `sudo certbot --nginx -d ajaydhungel.blog`
4. Configure Nginx to proxy to S3

## Option 4: Lambda@Edge + ACM

**Pros:**
- Serverless
- Uses ACM (Let's Encrypt equivalent)

**Cons:**
- More complex
- Requires CloudFront anyway

## Recommendation

**Use Option 1 (CloudFront + ACM)** - It's the easiest, most reliable, and ACM certificates are free just like Let's Encrypt. The setup is straightforward and fully managed.

## Quick CloudFront + ACM Setup

Would you like me to help you:
1. Create the ACM certificate request?
2. Set up the CloudFront distribution?
3. Configure the DNS records?

Let me know and I can provide the exact AWS CLI commands or guide you through the console steps!
