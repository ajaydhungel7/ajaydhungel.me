# Ajay's Hugo Profile

Welcome to my personal profile site built with Hugo using the [CharlolaMode theme](https://github.com/charlola/hugo-theme-charlolamode). This repository contains the necessary files to set up and customize your profile. Find this site on (https://ajaydhungel.blog)

## Features

- Responsive design
- Customizable layouts
- Easy integration of social media links
- Support for blog posts and portfolios
- **Content Management System (CMS)** - Edit content without code! See [CONTENT_EDITING.md](CONTENT_EDITING.md)

## Getting Started

### Prerequisites

Make sure you have [Hugo](https://gohugo.io/getting-started/installation/) and Git installed.

### Clone the Repository

Clone the template repository to your local machine:

```bash
git clone https://github.com/charlola/hugo-theme-charlolamode

```
Install the Theme

Change into the directory and initialize the theme:
```bash
cd your-repo-name
git submodule init
git submodule update
```
Run the Development Server

Run the Hugo development server:

```bash
hugo server
```
Access your profile at http://localhost:1313.

## Content Editing

**No code required!** Edit your site content easily:

1. **Using CMS (Recommended)**: Visit `https://ajaydhungel.blog/admin/` to use the visual content editor
2. **GitHub Web Editor**: Edit files directly on GitHub
3. **Local Development**: See [CONTENT_EDITING.md](CONTENT_EDITING.md) for detailed instructions

## Deployment

The site is automatically deployed to AWS S3 via GitHub Actions when you push to the `main` branch.

### Manual Deployment

If you need to deploy manually:

```bash
hugo --environment production
aws s3 sync public/ s3://ajaydhungel.me/ --delete
```
