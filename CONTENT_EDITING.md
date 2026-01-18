# Content Editing Guide

This guide explains how to edit your site content without making code-level changes.

## Option 1: Using Decap CMS (Recommended - No Code Required)

### Access the CMS
1. Go to `https://ajaydhungel.me/admin/` in your browser
2. Click "Login with GitHub"
3. Authorize the application
4. You'll see a user-friendly interface to edit your content

### What You Can Edit
- **Blog Posts**: Create, edit, and delete blog posts
- **About Page**: Update your about page content
- **Site Configuration**: Update site title, description, social links, etc.

### How It Works
- Changes are saved directly to your GitHub repository
- GitHub Actions automatically rebuilds and deploys your site
- No code editing required!

## Option 2: Direct GitHub Editing

### Edit Content Files
1. Go to your GitHub repository: `https://github.com/ajaydhungel7/ajaydhungel.me`
2. Navigate to the `content/` folder
3. Click on any `.md` file (like `content/about/about.md`)
4. Click the pencil icon to edit
5. Make your changes using Markdown
6. Commit the changes (they'll auto-deploy)

### File Locations
- **About Page**: `content/about/about.md`
- **Blog Posts**: `content/blog/` folder
- **Site Config**: `config.yml` (for site-wide settings)

## Option 3: Local Development (For Advanced Users)

### Quick Start
```bash
# Clone the repo (if not already)
git clone https://github.com/ajaydhungel7/ajaydhungel.me.git
cd ajaydhungel.me

# Run local server
hugo server

# Visit http://localhost:1313
```

### Create New Blog Post
```bash
hugo new blog/my-new-post.md
```

### Edit Content
- Edit files in `content/` folder
- Changes auto-reload in browser
- When done, commit and push to deploy

## Markdown Basics

Your content uses Markdown format. Here are the basics:

```markdown
# Heading 1
## Heading 2
### Heading 3

**Bold text**
*Italic text*

- Bullet point
- Another point

1. Numbered list
2. Second item

[Link text](https://example.com)

![Image alt text](/images/image.png)
```

## Common Tasks

### Update About Page
1. Use Decap CMS at `/admin/` OR
2. Edit `content/about/about.md` directly

### Add a Blog Post
1. Use Decap CMS: Go to `/admin/` → Blog Posts → New Post OR
2. Create a new file in `content/blog/your-post-name.md`

### Update Social Links
1. Use Decap CMS: Go to `/admin/` → Site Configuration OR
2. Edit `config.yml` → `params.socialIcons` section

### Change Profile Image
1. Upload new image to `static/images/` folder
2. Update `config.yml` → `params.profileMode.imageUrl` to point to new image

## Need Help?

- **Decap CMS Docs**: https://decapcms.org/docs/
- **Hugo Docs**: https://gohugo.io/documentation/
- **Markdown Guide**: https://www.markdownguide.org/
