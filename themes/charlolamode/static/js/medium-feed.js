// Multi-source Feed Widget
// Fetches and displays articles from multiple sources with thumbnails and titles

async function loadMultipleFeedsWidget(config) {
  try {
    const { sources, containerId, limit = null } = config;
    
    if (!sources || sources.length === 0) {
      console.error('No feed sources provided');
      return;
    }
    
    const container = document.getElementById(containerId);
    if (!container) {
      console.error(`Container with id "${containerId}" not found`);
      return;
    }
    
    container.innerHTML = '';
    
    // Fetch all articles from all sources
    const allArticles = [];
    
    for (const source of sources) {
      try {
        const items = await fetchFeedItems(source);
        if (!items || items.length === 0) continue;

        items.forEach(item => {
          allArticles.push({
            ...item,
            source: source.name
          });
        });
      } catch (error) {
        console.error(`Error loading ${source.name} feed:`, error);
      }
    }
    
    // Sort by date (newest first)
    allArticles.sort((a, b) => new Date(b.pubDate) - new Date(a.pubDate));
    
    // Deduplicate by title
    const seenTitles = new Set();
    const uniqueArticles = allArticles.filter(article => {
      if (seenTitles.has(article.title)) {
        return false;
      }
      seenTitles.add(article.title);
      return true;
    });
    
    // Limit if specified
    const articles = limit ? uniqueArticles.slice(0, limit) : uniqueArticles;
    
    const feedGrid = document.createElement('div');
    feedGrid.className = 'medium-feed-grid';
    
    articles.forEach(article => {
      const thumbnail = article.thumbnail || extractImageFromContent(article.content);
      const pubDate = new Date(article.pubDate).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
      
      const article_el = document.createElement('a');
      article_el.href = article.link;
      article_el.target = '_blank';
      article_el.rel = 'noopener noreferrer';
      article_el.className = 'medium-feed-item';
      
      article_el.innerHTML = `
        <div class="medium-feed-card">
          ${thumbnail ? `<div class="medium-feed-image"><img src="${thumbnail}" alt="${article.title}" loading="lazy"></div>` : ''}
          <div class="medium-feed-content">
            <h3 class="medium-feed-title">${article.title}</h3>
            <div class="medium-feed-meta">
              <span class="medium-feed-date">${pubDate}</span>
              <span class="medium-feed-source">${article.source}</span>
            </div>
          </div>
        </div>
      `;
      
      feedGrid.appendChild(article_el);
    });
    
    container.appendChild(feedGrid);
  } catch (error) {
    console.error('Error loading feeds:', error);
    const container = document.getElementById(containerId);
    if (container) {
      container.innerHTML = `<p class="medium-feed-error">Unable to load feeds. Please try again later.</p>`;
    }
  }
}

// Legacy single-feed function for backward compatibility
async function loadMediumFeed(username, containerId, limit = null) {
  loadMultipleFeedsWidget({
    sources: [{ type: 'medium', username, name: 'Medium' }],
    containerId,
    limit
  });
}

async function fetchFeedItems(source) {
  let rssUrl = '';

  if (source.type === 'medium') {
    rssUrl = `https://medium.com/feed/@${source.username}`;
  } else if (source.type === 'rss') {
    rssUrl = source.url;
  }

  if (!rssUrl) return [];

  return fetchRssItems(rssUrl);
}

async function fetchRssItems(rssUrl) {
  const strategies = [
    () => fetchRss2Json(rssUrl),
    () => fetchAllOriginsRss(rssUrl)
  ];

  let lastError = null;
  for (const strategy of strategies) {
    try {
      const items = await strategy();
      if (items && items.length > 0) return items;
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error('Unable to load RSS feed');
}

async function fetchRss2Json(rssUrl) {
  const feedUrl = `https://api.rss2json.com/v1/api.json?rss_url=${encodeURIComponent(rssUrl)}`;
  const response = await fetch(feedUrl);
  if (!response.ok) throw new Error('rss2json request failed');

  const data = await response.json();
  if (data.status && data.status !== 'ok') {
    throw new Error(data.message || 'rss2json error');
  }
  if (!data.items) return [];

  return data.items.map(item => ({
    title: item.title,
    link: item.link,
    pubDate: item.pubDate || item.pubdate || '',
    content: item.content || item.description || '',
    thumbnail: item.thumbnail || item.enclosure?.link || ''
  }));
}

async function fetchAllOriginsRss(rssUrl) {
  const feedUrl = `https://api.allorigins.win/raw?url=${encodeURIComponent(rssUrl)}`;
  const response = await fetch(feedUrl);
  if (!response.ok) throw new Error('allorigins request failed');

  const text = await response.text();
  return parseRssXml(text);
}

function parseRssXml(xmlText) {
  const parser = new DOMParser();
  const xml = parser.parseFromString(xmlText, 'text/xml');

  const items = Array.from(xml.querySelectorAll('item, entry'));
  return items.map(item => {
    const title = item.querySelector('title')?.textContent?.trim() || '';
    const linkEl = item.querySelector('link');
    const link = linkEl?.getAttribute('href') || linkEl?.textContent?.trim() || item.querySelector('guid')?.textContent?.trim() || '';
    const pubDate = item.querySelector('pubDate')?.textContent?.trim() || item.querySelector('updated')?.textContent?.trim() || '';
    const content =
      item.querySelector('content\\:encoded')?.textContent ||
      item.querySelector('content')?.textContent ||
      item.querySelector('description')?.textContent ||
      item.querySelector('summary')?.textContent ||
      '';
    const thumbnail =
      item.querySelector('media\\:thumbnail')?.getAttribute('url') ||
      item.querySelector('media\\:content')?.getAttribute('url') ||
      item.querySelector('enclosure')?.getAttribute('url') ||
      '';

    return {
      title,
      link,
      pubDate,
      content,
      thumbnail
    };
  });
}

function extractImageFromContent(html) {
  if (!html) return null;
  const img = html.match(/<img[^>]+src="([^">]+)"/);
  return img ? img[1] : null;
}

// Auto-initialize if data attribute is present
document.addEventListener('DOMContentLoaded', () => {
  // Handle new multi-source format
  const multiSourceElements = document.querySelectorAll('[data-feed-config]');
  multiSourceElements.forEach(el => {
    const config = JSON.parse(el.dataset.feedConfig);
    loadMultipleFeedsWidget({
      ...config,
      containerId: el.id
    });
  });
  
  // Handle legacy single-source format for backward compatibility
  const feedElements = document.querySelectorAll('[data-medium-feed]');
  feedElements.forEach(el => {
    const username = el.dataset.mediumFeed;
    const limit = parseInt(el.dataset.mediumLimit) || null;
    loadMediumFeed(username, el.id, limit);
  });
});
