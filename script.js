const root = document.documentElement;
const body = document.body;
const siteHeader = document.querySelector(".site-header");
const menuToggle = document.querySelector(".menu-toggle");
const headerPanel = document.querySelector(".header-panel");
const navLinks = document.querySelectorAll(".site-nav a");
const langButtons = document.querySelectorAll("[data-lang-switch]");
const reveals = document.querySelectorAll(".reveal");
const metaDescription = document.querySelector("#page-description");
const ogTitle = document.querySelector("#og-title");
const ogDescription = document.querySelector("#og-description");
const ogLocale = document.querySelector("#og-locale");
const configuredTranslations = window.translations || null;

function updateCurrentYear() {
  const year = new Date().getFullYear();
  document.querySelectorAll("[data-current-year]").forEach((node) => {
    node.textContent = String(year);
  });
}

function getPageTranslation(lang) {
  const page = body?.dataset?.page;
  return configuredTranslations?.[lang]?.pages?.[page] || null;
}

function hydrateConfiguredTranslations() {
  if (!configuredTranslations) return;

  ["en", "zh"].forEach((lang) => {
    const pageConfig = getPageTranslation(lang);
    if (!pageConfig?.items) return;

    document.querySelectorAll(`.lang-${lang}:not(img)`).forEach((node, index) => {
      const nextValue = pageConfig.items[index];
      if (typeof nextValue === "string") {
        node.innerHTML = nextValue;
      }
    });
  });
}

function updateMenuToggleLabel(lang, isOpen = siteHeader?.classList.contains("is-open")) {
  if (!menuToggle) return;

  const labels =
    lang === "zh"
      ? { open: "打开导航", close: "关闭导航" }
      : { open: "Open navigation", close: "Close navigation" };

  menuToggle.setAttribute("aria-label", isOpen ? labels.close : labels.open);
}

function setLanguage(lang) {
  const nextLang = lang === "zh" ? "zh" : "en";
  root.setAttribute("data-lang", nextLang);
  root.setAttribute("lang", nextLang === "zh" ? "zh-CN" : "en");

  const pageConfig = getPageTranslation(nextLang);
  const titleKey = nextLang === "zh" ? "titleZh" : "titleEn";
  const descriptionKey = nextLang === "zh" ? "descriptionZh" : "descriptionEn";
  const nextTitle = pageConfig?.meta?.title || body?.dataset?.[titleKey];
  const nextDescription = pageConfig?.meta?.description || body?.dataset?.[descriptionKey];

  if (nextTitle) {
    document.title = nextTitle;
  }

  if (ogTitle) {
    ogTitle.setAttribute("content", document.title);
  }

  if (metaDescription && nextDescription) {
    metaDescription.setAttribute("content", nextDescription);

    if (ogDescription) {
      ogDescription.setAttribute("content", nextDescription);
    }
  }

  if (ogLocale) {
    ogLocale.setAttribute("content", nextLang === "zh" ? "zh_CN" : "en_US");
  }

  langButtons.forEach((button) => {
    const active = button.dataset.langSwitch === nextLang;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });

  updateMenuToggleLabel(nextLang);
  localStorage.setItem("site-language", nextLang);
}

function initLanguage() {
  const saved = localStorage.getItem("site-language");
  setLanguage(saved || "en");
}

function closeMenu() {
  if (!siteHeader || !menuToggle) return;
  siteHeader.classList.remove("is-open");
  menuToggle.setAttribute("aria-expanded", "false");
  updateMenuToggleLabel(root.getAttribute("data-lang") === "zh" ? "zh" : "en", false);
}

function initMenu() {
  if (!menuToggle || !siteHeader || !headerPanel) return;

  menuToggle.addEventListener("click", () => {
    const isOpen = siteHeader.classList.toggle("is-open");
    menuToggle.setAttribute("aria-expanded", String(isOpen));
    updateMenuToggleLabel(root.getAttribute("data-lang") === "zh" ? "zh" : "en", isOpen);
  });

  navLinks.forEach((link) => {
    link.addEventListener("click", closeMenu);
  });

  document.addEventListener("click", (event) => {
    if (!siteHeader.classList.contains("is-open")) return;
    if (siteHeader.contains(event.target)) return;
    closeMenu();
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 980) {
      closeMenu();
    }
  });
}

function initLanguageButtons() {
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

hydrateConfiguredTranslations();
initLanguage();
updateCurrentYear();
initMenu();
initLanguageButtons();
initReveal();
