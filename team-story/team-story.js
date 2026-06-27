const root = document.documentElement;
const body = document.body;
const langButtons = document.querySelectorAll("[data-lang-switch]");
const metaDescription = document.querySelector("#page-description");
const ogTitle = document.querySelector("#og-title");
const ogDescription = document.querySelector("#og-description");
const ogLocale = document.querySelector("#og-locale");
const archive = window.teamArchive || null;

root.classList.add("js-enabled");

function readSavedLanguage() {
  try {
    return localStorage.getItem("site-language");
  } catch (error) {
    return null;
  }
}

function saveLanguage(lang) {
  try {
    localStorage.setItem("site-language", lang);
  } catch (error) {
    return;
  }
}

function updateCurrentYear() {
  const year = new Date().getFullYear();
  document.querySelectorAll("[data-current-year]").forEach((node) => {
    node.textContent = String(year);
  });
}

function setLanguage(lang) {
  const nextLang = lang === "en" ? "en" : "zh";
  root.setAttribute("data-lang", nextLang);
  root.setAttribute("lang", nextLang === "zh" ? "zh-CN" : "en");

  const title = nextLang === "zh" ? body.dataset.titleZh : body.dataset.titleEn;
  const description = nextLang === "zh" ? body.dataset.descriptionZh : body.dataset.descriptionEn;

  if (title) document.title = title;
  if (metaDescription && description) metaDescription.setAttribute("content", description);
  if (ogTitle) ogTitle.setAttribute("content", document.title);
  if (ogDescription && description) ogDescription.setAttribute("content", description);
  if (ogLocale) ogLocale.setAttribute("content", nextLang === "zh" ? "zh_CN" : "en_US");

  langButtons.forEach((button) => {
    const active = button.dataset.langSwitch === nextLang;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });

  saveLanguage(nextLang);
}

function initLanguage() {
  setLanguage(readSavedLanguage() || "zh");
  langButtons.forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.langSwitch));
  });
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function articleMap() {
  if (!archive) return new Map();
  return new Map(archive.articles.map((article) => [article.id, article]));
}

const articlesById = articleMap();

function getArticle(id) {
  return articlesById.get(id) || null;
}

function detailUrl(article) {
  return article ? `./detail.html?id=${encodeURIComponent(article.id)}` : "./submit.html";
}

function detailLink(article, label = "查看完整记录") {
  if (!article) return "";
  return `<a class="inline-link" href="${escapeHtml(detailUrl(article))}">${escapeHtml(label)}</a>`;
}

function imageMarkup(article, className = "article-thumb") {
  if (!article || !article.image) {
    return "";
  }

  const imageInfo = article.images?.find((item) => item.src === article.image) || article.images?.[0] || {};
  const width = imageInfo.width ? ` width="${escapeHtml(imageInfo.width)}"` : "";
  const height = imageInfo.height ? ` height="${escapeHtml(imageInfo.height)}"` : "";
  const loading = className === "team-photo" ? "eager" : "lazy";
  return `
    <figure class="${className}">
      <img src="${escapeHtml(article.image)}" alt="${escapeHtml(article.title)}" loading="${loading}" decoding="async"${width}${height}>
    </figure>
  `;
}

function detailSections(article, className = "inline-detail-sections") {
  const sections = article?.detail?.sections || [];
  if (!sections.length) return "";

  return `
    <div class="${className}">
      ${sections
        .map(
          (section) => `
            <section>
              <h4>${escapeHtml(section.heading)}</h4>
              <p>${escapeHtml(section.body)}</p>
            </section>
          `
        )
        .join("")}
    </div>
  `;
}

function highlightList(article, className = "inline-highlights") {
  const highlights = article?.highlights || [];
  if (!highlights.length) return "";

  return `
    <ul class="${className}">
      ${highlights.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}
    </ul>
  `;
}

function inlineImageGallery(article, className = "inline-image-gallery", limit = 2, offset = 0) {
  const images = (article?.images || []).slice(offset, offset + limit);
  if (!images.length) return "";

  return `
    <div class="${className} ${images.length === 1 ? "single-image" : ""}">
      ${images
        .map(
          (imageItem) => {
            const width = imageItem.width ? ` width="${escapeHtml(imageItem.width)}"` : "";
            const height = imageItem.height ? ` height="${escapeHtml(imageItem.height)}"` : "";
            return `
              <figure>
                <img src="${escapeHtml(imageItem.src)}" alt="${escapeHtml(article.displayTitle || article.title)}" loading="eager" decoding="async"${width}${height}>
              </figure>
            `;
          }
        )
        .join("")}
    </div>
  `;
}

function timelinePhotoCard(article, className = "timeline-photo") {
  if (!article?.image) return "";
  const imageInfo = article.images?.find((item) => item.src === article.image) || article.images?.[0] || {};
  const width = imageInfo.width ? ` width="${escapeHtml(imageInfo.width)}"` : "";
  const height = imageInfo.height ? ` height="${escapeHtml(imageInfo.height)}"` : "";

  return `
    <figure class="${className}">
      <img src="${escapeHtml(article.image)}" alt="${escapeHtml(article.displayTitle || article.title)}" loading="eager" decoding="async"${width}${height}>
      <figcaption>
        <span>${escapeHtml(article.date.slice(0, 4))}</span>
        <strong>${escapeHtml(article.displayTitle || article.title)}</strong>
      </figcaption>
    </figure>
  `;
}

function yearStoryImage(article) {
  if (!article?.image) return "";
  const imageInfo = article.images?.find((item) => item.src === article.image) || article.images?.[0] || {};
  const width = imageInfo.width ? ` width="${escapeHtml(imageInfo.width)}"` : "";
  const height = imageInfo.height ? ` height="${escapeHtml(imageInfo.height)}"` : "";

  return `
    <figure class="year-story-photo">
      <img src="${escapeHtml(article.image)}" alt="${escapeHtml(article.displayTitle || article.title)}" loading="eager" decoding="async"${width}${height}>
    </figure>
  `;
}

function timelinePhotoGallery(items) {
  const articles = items.filter((article) => article?.image);
  if (!articles.length) return "";

  return `
    <div class="timeline-gallery ${articles.length === 1 ? "single-image" : ""}">
      ${articles.map((article) => timelinePhotoCard(article, "timeline-gallery-card")).join("")}
    </div>
  `;
}

function timelineMedia(primaryArticle, extraArticles = []) {
  const articles = [primaryArticle, ...extraArticles].filter((article) => article?.image);
  if (!articles.length) return "";

  return `
    <div class="timeline-media ${articles.length === 1 ? "single-image" : ""}">
      ${articles.map((article) => timelinePhotoCard(article, "timeline-media-card")).join("")}
    </div>
  `;
}

function teamMedia(article) {
  const mediaMarkup = `${imageMarkup(article, "team-photo")}${inlineImageGallery(article, "team-inline-gallery", 2, article?.image ? 1 : 0)}`;
  if (!mediaMarkup.trim()) return "";

  return `<div class="team-card-media">${mediaMarkup}</div>`;
}

function articleCard(article, options = {}) {
  const highlights = options.detail && article.highlights.length
    ? `<ul class="article-highlights">${article.highlights.slice(0, 2).map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>`
    : "";
  const status = "";
  const link = options.link === false ? "" : detailLink(article);

  return `
    <article class="article-card ${article.image ? "" : "no-image"}">
      ${imageMarkup(article)}
      <div class="article-copy">
        <div class="article-meta">
          <span class="category-pill category-${escapeHtml(article.category)}">${escapeHtml(article.categoryLabel)}</span>
          <time datetime="${escapeHtml(article.date)}">${escapeHtml(article.dateLabel)}</time>
          ${status}
        </div>
        <h3 class="card-title">${escapeHtml(article.displayTitle || article.title)}</h3>
        <p>${escapeHtml(article.excerpt)}</p>
        ${highlights}
        ${link}
      </div>
    </article>
  `;
}

function renderStats() {
  if (!archive) return;
  document.querySelectorAll("[data-stat]").forEach((node) => {
    const key = node.dataset.stat;
    if (Object.prototype.hasOwnProperty.call(archive.stats, key)) {
      node.textContent = String(archive.stats[key]);
    }
  });
}

function renderMilestones() {
  if (!archive) return;
  document.querySelectorAll('[data-render="milestones"]').forEach((container) => {
    container.innerHTML = archive.milestones
      .map((item) => {
        const article = getArticle(item.articleId);
        const awardArticle = getArticle(item.awardArticleId) || article;
        const imageArticle = article?.image ? article : awardArticle?.image ? awardArticle : null;
        const awards = item.awards || [];
        return `
          <article class="timeline-item year-story ${imageArticle?.image ? "has-photo" : "no-photo"}">
            <div class="year-story-media">
              ${imageArticle?.image ? yearStoryImage(imageArticle) : `<div class="year-story-placeholder"><span>${escapeHtml(item.year)}</span></div>`}
            </div>
            <div class="timeline-body year-story-copy">
              <p class="timeline-year">${escapeHtml(item.year)}</p>
              <h3>${escapeHtml(item.title)}</h3>
              <p>${escapeHtml(item.body)}</p>
              ${awards.length ? `
                <ul class="award-list">
                  ${awards.map((award) => `<li>${escapeHtml(award)}</li>`).join("")}
                </ul>
              ` : ""}
            </div>
          </article>
        `;
      })
      .join("");
  });
}

function renderFeaturedArticles() {
  if (!archive) return;
  document.querySelectorAll('[data-render="featured"]').forEach((container) => {
    const articles = archive.featuredIds.map(getArticle).filter(Boolean);
    container.innerHTML = articles.map((article) => articleCard(article, { detail: false, link: false })).join("");
  });
}

function filteredArticles(container) {
  const filter = container.dataset.filter || "all";
  const sort = container.dataset.sort || "asc";
  const limit = Number.parseInt(container.dataset.limit || "0", 10);
  const detail = container.dataset.detail === "true";
  let items = archive.articles.slice();

  if (filter !== "all") {
    items = items.filter((article) => article.category === filter);
  }

  items.sort((a, b) => (sort === "desc" ? b.date.localeCompare(a.date) : a.date.localeCompare(b.date)));
  if (limit > 0) {
    items = items.slice(0, limit);
  }

  return { items, detail };
}

function renderArticles() {
  if (!archive) return;
  document.querySelectorAll('[data-render="articles"]').forEach((container) => {
    const { items, detail } = filteredArticles(container);
    container.innerHTML = items.map((article) => articleCard(article, { detail })).join("");
  });
}

function renderCategoryTabs() {
  if (!archive) return;
  document.querySelectorAll('[data-render="category-tabs"]').forEach((container) => {
    const targetSelector = container.dataset.target;
    const categories = [
      ["all", "全部内容"],
      ["competition", archive.categoryLabels.competition],
      ["community", archive.categoryLabels.community],
      ["technical", archive.categoryLabels.technical],
      ["outreach", archive.categoryLabels.outreach],
      ["activity", archive.categoryLabels.activity],
    ];

    container.innerHTML = categories
      .map(([key, label], index) => `<button type="button" class="${index === 0 ? "is-active" : ""}" data-category="${key}">${escapeHtml(label)}</button>`)
      .join("");

    container.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-category]");
      if (!button) return;
      container.querySelectorAll("button").forEach((item) => item.classList.toggle("is-active", item === button));
      const target = targetSelector ? document.querySelector(targetSelector) : null;
      if (target) {
        target.dataset.filter = button.dataset.category;
        renderArticles();
      }
    });
  });
}

function renderAwards() {
  if (!archive) return;
  document.querySelectorAll('[data-render="awards"]').forEach((container) => {
    container.innerHTML = archive.awards
      .map((award) => {
        const article = getArticle(award.articleId);
        return `
          <article class="award-row">
            <div class="award-year">${escapeHtml(award.year)}</div>
            <div>
              <h3 class="card-title">${escapeHtml(award.title)}</h3>
              <p>${escapeHtml(award.body)}</p>
              ${detailLink(article, "查看赛事记录")}
            </div>
            <div class="award-meta">${article ? escapeHtml(article.displayTitle || article.title) : "G_Robot"}</div>
          </article>
        `;
      })
      .join("");
  });
}

function renderTeams() {
  if (!archive) return;
  document.querySelectorAll('[data-render="teams"]').forEach((container) => {
    container.innerHTML = archive.teamTimeline
      .map((item) => {
        const article = getArticle(item.articleId);
        return `
          <article class="photo-card team-card ${article?.image ? "" : "no-image"}">
            <div class="team-card-main">
              <div class="team-card-copy">
                <div class="team-card-heading">
                  <p class="timeline-year">${escapeHtml(item.period)}</p>
                  <h3 class="card-title">${escapeHtml(item.title)}</h3>
                </div>
                <p class="team-intro">${escapeHtml(item.body)}</p>
                <p class="team-people">${escapeHtml(item.people)}</p>
                ${article ? `<p class="team-summary">${escapeHtml(article.detail?.summary || article.excerpt)}</p>` : ""}
                ${highlightList(article, "team-highlights")}
                ${detailSections(article, "team-detail-sections")}
              </div>
              ${teamMedia(article)}
            </div>
          </article>
        `;
      })
      .join("");
  });
}

function renderSources() {
  if (!archive) return;
  document.querySelectorAll('[data-render="sources"]').forEach((container) => {
    container.innerHTML = archive.articles
      .map((article) => `
        <article class="source-row">
          <div>
            <time datetime="${escapeHtml(article.date)}">${escapeHtml(article.dateLabel)}</time>
            <span class="category-pill category-${escapeHtml(article.category)}">${escapeHtml(article.categoryLabel)}</span>
          </div>
          <h3>${escapeHtml(article.displayTitle || article.title)}</h3>
          ${detailLink(article)}
        </article>
      `)
      .join("");
  });
}

function renderDetailPage() {
  if (!archive || !document.querySelector("[data-render-detail]")) return;

  const params = new URLSearchParams(window.location.search);
  const article = getArticle(params.get("id")) || archive.articles[archive.articles.length - 1];
  if (!article) return;

  document.querySelectorAll("[data-detail-title]").forEach((node) => {
    node.textContent = article.displayTitle || article.title;
  });
  document.querySelectorAll("[data-detail-date]").forEach((node) => {
    node.textContent = article.dateLabel;
    node.setAttribute("datetime", article.date);
  });
  document.querySelectorAll("[data-detail-category]").forEach((node) => {
    node.textContent = article.categoryLabel;
  });
  document.querySelectorAll("[data-detail-summary]").forEach((node) => {
    node.textContent = article.detail?.summary || article.excerpt;
  });
  const image = document.querySelector("[data-detail-image]");
  if (image) {
    const figure = image.closest("figure");
    if (article.image) {
      image.setAttribute("src", article.image);
      image.setAttribute("alt", article.displayTitle || article.title);
      figure?.classList.remove("is-empty");
    } else {
      image.removeAttribute("src");
      image.setAttribute("alt", "");
      figure?.classList.add("is-empty");
      image.remove();
    }
  }
  document.querySelectorAll("[data-detail-layout]").forEach((node) => {
    node.classList.toggle("no-main-image", !article.image);
  });

  document.querySelectorAll("[data-render-detail-sections]").forEach((container) => {
    const sections = article.detail?.sections || [];
    container.innerHTML = sections
      .map((section) => `
        <article class="detail-section">
          <h2>${escapeHtml(section.heading)}</h2>
          <p>${escapeHtml(section.body)}</p>
        </article>
      `)
      .join("");
  });

  document.querySelectorAll("[data-render-detail-gallery]").forEach((container) => {
    const images = article.images || [];
    container.closest("[data-detail-gallery-section]")?.classList.toggle("is-hidden", images.length === 0);
    container.innerHTML = images
      .map((imageItem) => `
        <figure>
          <img src="${escapeHtml(imageItem.src)}" alt="${escapeHtml(article.displayTitle || article.title)}" loading="lazy" decoding="async">
        </figure>
      `)
      .join("");
  });

  const related = archive.articles
    .filter((item) => item.id !== article.id && item.category === article.category)
    .sort((a, b) => Math.abs(a.year - article.year) - Math.abs(b.year - article.year))
    .slice(0, 3);
  document.querySelectorAll("[data-render-related]").forEach((container) => {
    container.innerHTML = related.map((item) => articleCard(item)).join("");
  });
}

function renderArchive() {
  if (!archive) return;
  renderStats();
  renderMilestones();
  renderFeaturedArticles();
  renderCategoryTabs();
  renderArticles();
  renderAwards();
  renderTeams();
  renderSources();
  renderDetailPage();
}

function initReveal() {
  const reveals = document.querySelectorAll(".reveal");
  if (!("IntersectionObserver" in window)) {
    reveals.forEach((item) => item.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.14 }
  );

  reveals.forEach((item) => observer.observe(item));

  const revealInitialViewport = () => {
    reveals.forEach((item) => {
      const rect = item.getBoundingClientRect();
      if (rect.top < window.innerHeight && rect.bottom > 0) {
        item.classList.add("is-visible");
        observer.unobserve(item);
      }
    });
  };

  requestAnimationFrame(revealInitialViewport);
  setTimeout(revealInitialViewport, 120);
}

function initImageFallbacks() {
  document.querySelectorAll("img[data-fallback]").forEach((image) => {
    image.addEventListener("error", () => {
      const fallback = image.dataset.fallback;
      if (fallback && image.getAttribute("src") !== fallback) {
        image.setAttribute("src", fallback);
      }
    });
  });
}

initLanguage();
updateCurrentYear();
renderArchive();
initReveal();
initImageFallbacks();
