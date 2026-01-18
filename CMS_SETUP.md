# Decap CMS Setup Guide

## Quick Start

1. **Deploy the changes** - The CMS files are already set up in `static/admin/`
2. **Access the CMS** - Go to `https://ajaydhungel.blog/admin/` after deployment
3. **Login** - Click "Login with GitHub" and authorize
4. **Start editing!** - You'll see a user-friendly interface

## How It Works

- Decap CMS uses GitHub OAuth (PKCE) for authentication
- No backend server needed - it commits directly to your GitHub repo
- Changes automatically trigger your GitHub Actions workflow
- Site rebuilds and deploys automatically

## What You Can Edit

### Currently Available:
- ✅ **Blog Posts** - Create, edit, and delete individual blog posts! 🎉
- ✅ **About Page** - Edit your about page content
- ✅ **Blog Page** - Edit your blog listing page
- ✅ **Site Configuration** - Edit site title, description, social links

### How to Create a Blog Post:
1. Go to `https://ajaydhungel.blog/admin/`
2. Click "Blog Posts" in the sidebar
3. Click "New Blog Post"
4. Fill in:
   - Title
   - Publish Date
   - Content (Markdown)
   - Tags (optional)
   - Description (optional, for SEO)
5. Set `draft: false` when ready to publish
6. Click "Publish"

Posts are saved to `content/articles/` and will appear on your site automatically!

## Troubleshooting

### "Failed to load config.yml"
- Make sure the file exists at `static/admin/config.yml`
- Check that the repo name matches: `ajaydhungel7/ajaydhungel.me`

### "Authentication failed"
- Make sure you're logged into GitHub
- Try clearing browser cache
- PKCE auth should work automatically for public repos

### Changes not appearing
- Check GitHub Actions workflow status
- Verify the commit was created in your repo
- Wait a few minutes for deployment to complete

## Customization

To add more editable content, edit `static/admin/config.yml`. See [Decap CMS Documentation](https://decapcms.org/docs/) for more options.
