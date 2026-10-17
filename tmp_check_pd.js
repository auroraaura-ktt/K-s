/* Temporary verification harness for the Project Details CSS.
   Renders the real Django page snapshot in Chrome (headless shell) at many
   viewport sizes and reports overflow / layout / typography problems. */
const path = require('path');
const puppeteer = require('puppeteer');

const BROWSERS = {
  chrome: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  edge: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
};
const BROWSER = process.env.BROWSER || 'chrome';
const SHELL = BROWSERS[BROWSER];
const BASE = `http://127.0.0.1:${process.env.PORT || 8899}/`;

const PAGES = [
  { file: 'tmp_pd_render.html', label: 'care-connect' },
  { file: 'tmp_pd_render_hostile.html', label: 'hostile-text' },
  { file: 'tmp_pd_render_auth.html', label: 'signed-in' },
];

const VIEWPORTS = [
  [320, 640], [360, 740], [375, 812], [390, 844], [414, 896], [480, 800],
  [767, 900], [768, 1024], [820, 1180], [1024, 768], [1280, 800],
  [1440, 900], [1920, 1080],
];

function hasRule(selector) {
  for (const sheet of Array.from(document.styleSheets)) {
    let rules;
    try { rules = sheet.cssRules; } catch (e) { continue; }
    for (const rule of Array.from(rules)) {
      if (rule.selectorText === selector) return true;
    }
  }
  return false;
}

function collect() {
  const hasRule = (selector) => {
    for (const sheet of Array.from(document.styleSheets)) {
      let rules;
      try { rules = sheet.cssRules; } catch (e) { continue; }
      for (const rule of Array.from(rules)) {
        if (rule.selectorText === selector) return true;
      }
    }
    return false;
  };
  const vw = window.innerWidth;
  const q = (s) => document.querySelector(s);
  const cs = (el, props) => {
    if (!el) return null;
    const out = {};
    props.forEach((p) => { out[p] = getComputedStyle(el).getPropertyValue(p); });
    return out;
  };

  const offenders = [];
  document.querySelectorAll('body *').forEach((el) => {
    const style = getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return;
    if (el.tagName === 'HTML' || el.tagName === 'BODY') return;
    if (el.closest('dialog:not([open])')) return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    if (r.right > vw + 1 || r.left < -1) {
      offenders.push({
        tag: el.tagName.toLowerCase(),
        cls: (typeof el.className === 'string' ? el.className : '').slice(0, 60),
        left: Math.round(r.left),
        right: Math.round(r.right),
      });
    }
  });

  const distorted = [];
  document.querySelectorAll('body img').forEach((img) => {
    if (img.closest('dialog:not([open])')) return;
    const r = img.getBoundingClientRect();
    const fit = getComputedStyle(img).objectFit;
    if (!img.naturalWidth || !r.width || !r.height) return;
    if (fit === 'contain' || fit === 'cover' || fit === 'none' || fit === 'scale-down') return;
    const natural = img.naturalWidth / img.naturalHeight;
    const box = r.width / r.height;
    if (Math.abs(natural - box) / natural > 0.02) {
      distorted.push({ cls: img.className, src: img.getAttribute('src'), fit, natural: natural.toFixed(3), box: box.toFixed(3) });
    }
  });

  const textOverflow = [];
  document.querySelectorAll('.project-details-inner p, .project-details-inner h1, .project-details-inner h2, .project-details-inner li, .project-details-inner dd, .project-details-inner dt')
    .forEach((el) => {
      if (el.scrollWidth > el.clientWidth + 1) {
        textOverflow.push({ tag: el.tagName, cls: el.className, scroll: el.scrollWidth, client: el.clientWidth });
      }
    });

  const content = q('.project-details-content');
  const info = q('.project-details-info');
  const inner = q('.project-details-inner');
  const viewer = q('.project-media-viewer');
  const actions = q('.pd-actions');
  const prose = q('.pd-prose p');
  const summary = q('.pd-summary');
  const title = q('.pd-title');
  const heading = q('.pd-section h2');
  const buttons = Array.from(document.querySelectorAll('.pd-actions .pd-btn')).map((b) => {
    const r = b.getBoundingClientRect();
    return { text: b.textContent.trim().slice(0, 22), w: Math.round(r.width), h: Math.round(r.height), right: Math.round(r.right) };
  });

  const primary = document.querySelector('.pd-btn-primary');
  if (primary) primary.focus();
  const focusStyle = primary
    ? { width: getComputedStyle(primary).outlineWidth, style: getComputedStyle(primary).outlineStyle }
    : null;
  if (document.activeElement && document.activeElement.blur) document.activeElement.blur();

  return {
    viewport: { width: vw, height: window.innerHeight },
    infoScroll: info ? { scrollH: Math.round(info.scrollHeight), clientH: Math.round(info.clientHeight) } : null,
    focusStyle: focusStyle,
    docScrollWidth: document.documentElement.scrollWidth,
    docClientWidth: document.documentElement.clientWidth,
    docScrollHeight: document.documentElement.scrollHeight,
    offenders: offenders.slice(0, 8),
    offenderCount: offenders.length,
    distorted,
    textOverflow,
    content: cs(content, ['display', 'grid-template-columns', 'flex-direction', 'height', 'min-height', 'gap']),
    info: cs(info, ['height', 'overflow-y', 'overflow-x', 'border-radius']),
    inner: cs(inner, ['padding', 'max-width', 'min-width', 'overflow-wrap']),
    viewer: cs(viewer, ['height', 'min-height', 'max-height']),
    actions: cs(actions, ['display', 'flex-wrap', 'gap', 'margin-bottom']),
    prose: cs(prose, ['text-align', 'font-size', 'line-height']),
    summary: cs(summary, ['text-align']),
    title: cs(title, ['text-align', 'font-size']),
    heading: cs(heading, ['text-align', 'margin-top']),
    buttons,
    sheetRules: {
      content: hasRule('.project-details-content'),
      inner: hasRule('.project-details-inner'),
      actions: hasRule('.pd-actions'),
      metaDd: hasRule('.pd-meta-item dd'),
      proseJustify: hasRule('.pd-prose p'),
    },
  };
}

function lightboxReport() {
  const dialog = document.querySelector('[data-ab-lightbox]');
  const slide = document.querySelector('.project-media-viewer .ab-slide');
  if (!dialog || !slide) return { skipped: true };
  slide.click();
  const img = dialog.querySelector('img');
  const imgRect = img.getBoundingClientRect();
  const dialogRect = dialog.getBoundingClientRect();
  const out = {
    open: dialog.open,
    dialog: { w: Math.round(dialogRect.width), h: Math.round(dialogRect.height) },
    img: { w: Math.round(imgRect.width), h: Math.round(imgRect.height), right: Math.round(imgRect.right), bottom: Math.round(imgRect.bottom) },
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight,
    docScrollWidth: document.documentElement.scrollWidth,
    fits: imgRect.right <= window.innerWidth + 1 && imgRect.bottom <= window.innerHeight + 1 && imgRect.left >= -1 && imgRect.top >= -1,
  };
  dialog.close();
  return out;
}
(async () => {
  const browser = await puppeteer.launch({
    executablePath: SHELL,
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });

  const page = await browser.newPage();
  page.on('pageerror', (e) => console.log('PAGE ERROR:', e.message));
  page.on('requestfailed', (r) => {
    if (!/fonts|fontawesome|cdnjs/.test(r.url())) console.log('REQ FAIL:', r.url());
  });

  const problems = [];
  for (const target of PAGES) {
    const fileUrl = BASE + target.file;
    for (const [width, height] of VIEWPORTS) {
      await page.setViewport({ width, height, deviceScaleFactor: 1 });
      await page.goto(fileUrl, { waitUntil: 'load', timeout: 60000 });
      const report = await page.evaluate(collect);
      const fails = [];
      if (report.docScrollWidth > report.docClientWidth + 1) fails.push(`doc overflow ${report.docScrollWidth}>${report.docClientWidth}`);
      if (report.offenderCount) fails.push(`${report.offenderCount} offenders ${JSON.stringify(report.offenders)}`);
      if (report.distorted.length) fails.push(`distorted imgs ${JSON.stringify(report.distorted)}`);
      if (report.textOverflow.length) fails.push(`text overflow ${JSON.stringify(report.textOverflow)}`);
      if (width >= 768 && report.content.display !== 'grid') fails.push(`desktop display=${report.content.display}`);
      if (width < 768 && report.content.display !== 'flex') fails.push(`mobile display=${report.content.display}`);
      if (report.prose['text-align'] !== 'justify') fails.push(`prose align=${report.prose['text-align']}`);
      if (report.summary['text-align'] !== 'justify') fails.push(`summary align=${report.summary['text-align']}`);
      if (report.title['text-align'] === 'justify') fails.push('title justified');
      if (report.heading['text-align'] === 'justify') fails.push('heading justified');
      if (report.buttons.length === 0) fails.push('no action buttons');
      if (report.buttons.some((b) => b.h < 30 || b.w < 55)) fails.push(`button too small ${JSON.stringify(report.buttons)}`);
      if (report.buttons.some((b) => b.right > width + 1)) fails.push(`button past viewport ${JSON.stringify(report.buttons)}`);
      if (width >= 768 && !(report.infoScroll.scrollH > report.infoScroll.clientH)) {
        fails.push(`desktop panel not scrolling ${JSON.stringify(report.infoScroll)}`);
      }
      if (width < 768 && report.info['overflow-y'] !== 'visible') {
        fails.push(`mobile panel overflow-y=${report.info['overflow-y']}`);
      }
      if (!report.focusStyle || report.focusStyle.style !== 'solid' || parseFloat(report.focusStyle.width) < 1) {
        fails.push(`no visible focus ring ${JSON.stringify(report.focusStyle)}`);
      }
      Object.entries(report.sheetRules).forEach(([k, v]) => { if (!v) fails.push(`css rule missing: ${k}`); });
      const row = `${target.label.padEnd(14)} ${String(width).padStart(4)}x${String(height).padEnd(4)} ` +
        `display=${(report.content.display || '').padEnd(5)} cols="${(report.content['grid-template-columns'] || '').slice(0, 44)}" ` +
        `panelH=${report.info.height} pageScrollW=${report.docScrollWidth}/${report.docClientWidth}`;
      console.log((fails.length ? 'FAIL ' : 'ok   ') + row);
      if (fails.length) {
        problems.push({ target: target.label, width, fails });
        fails.forEach((f) => console.log('        -> ' + f));
      }
    }
  }

  for (const [width, height] of [[1440, 900], [390, 844]]) {
    await page.setViewport({ width, height, deviceScaleFactor: 1 });
    await page.goto(BASE + 'tmp_pd_render.html', { waitUntil: 'load' });
    const lb = await page.evaluate(lightboxReport);
    const ok = lb.skipped || (lb.open && lb.fits && lb.docScrollWidth <= width + 1);
    console.log(`${ok ? 'ok   ' : 'FAIL '}lightbox ${width}x${height} ${JSON.stringify(lb)}`);
    if (!ok) problems.push({ target: 'lightbox', width, fails: ['lightbox'] });
  }

  const shots = [
    ['desktop-1440', 1440, 900, 'tmp_pd_render.html'],
    ['tablet-820', 820, 1180, 'tmp_pd_render.html'],
    ['mobile-390', 390, 844, 'tmp_pd_render.html'],
    ['mobile-320-hostile', 320, 640, 'tmp_pd_render_hostile.html'],
  ];
  for (const [name, width, height, file] of shots) {
    await page.setViewport({ width, height, deviceScaleFactor: 1 });
    await page.goto(BASE + file, { waitUntil: 'load' });
    await page.screenshot({ path: `tmp_shot_${name}.png`, fullPage: true });
    console.log('shot tmp_shot_' + name + '.png');
  }

  console.log('\nsummary: ' + (problems.length ? `${problems.length} failing combinations` : 'all checks passed'));
  await browser.close();
})();

