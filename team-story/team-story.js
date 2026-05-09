const root = document.documentElement;
const body = document.body;
const langButtons = document.querySelectorAll("[data-lang-switch]");
const metaDescription = document.querySelector("#page-description");
const ogTitle = document.querySelector("#og-title");
const ogDescription = document.querySelector("#og-description");
const ogLocale = document.querySelector("#og-locale");
const reveals = document.querySelectorAll(".reveal");

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
  const nextLang = lang === "zh" ? "zh" : "en";
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
  setLanguage(readSavedLanguage() || "en");
  langButtons.forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.langSwitch));
  });
}

function initReveal() {
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
initReveal();
initImageFallbacks();
