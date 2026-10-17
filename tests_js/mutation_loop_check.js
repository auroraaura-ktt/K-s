/*
 * Regression check for the Project Details page freeze.
 *
 * Reads {"code": "<inline script>"} on stdin, renders gallery markup,
 * then tests thumbnail selection and lightbox navigation in a real DOM.
 *
 * A MutationObserver that observes the same element it mutates will re-trigger
 * itself forever and peg the CPU -- that was the original "page is unresponsive"
 * bug. This exits non-zero if the callback budget is blown.
 *
 * Usage: node tests_js/mutation_loop_check.js  < payload.json
 */
'use strict';

const { JSDOM } = require('jsdom');

const MAX_MUTATIONS = 500;

function buildMarkup(photoCount) {
  const slides = [];
  for (let i = 0; i < photoCount; i += 1) {
    slides.push(
      '<button class="ab-slide' + (i === 0 ? ' active' : '') + '" data-ab-slide="' + i + '">' +
        '<img src="/media/projects/p' + i + '.png" alt="photo ' + i + '">' +
      '</button>'
    );
  }
  const thumbnails = [];
  for (let i = 0; i < Math.min(photoCount, 4); i += 1) {
    thumbnails.push(
      '<button class="ab-thumbnail' + (i === 0 ? ' active' : '') +
      '" data-ab-thumb="' + i + '" aria-pressed="' + (i === 0) + '">' +
      '<img src="/media/projects/p' + i + '.png" alt="">' +
      (i === 3 && photoCount > 4 ? '<span data-ab-open-gallery>+ ' + (photoCount - 4) + ' more</span>' : '') +
      '</button>'
    );
  }
  return (
    '<div class="ab-container ab-project">' +
      '<div class="ab-photo">' +
        '<div class="ab-slideshow" data-ab-slideshow>' + slides.join('') + '</div>' +
        '<div class="ab-counter" data-ab-counter>1 / ' + photoCount + '</div>' +
        '<button class="ab-prev" data-ab-prev></button>' +
        '<button class="ab-next" data-ab-next></button>' +
        '<div class="ab-thumbnails">' + thumbnails.join('') + '</div>' +
        '<dialog data-ab-lightbox>' +
          '<span data-ab-lightbox-counter></span>' +
          '<button data-ab-close></button>' +
          '<button data-ab-lightbox-prev></button>' +
          '<img data-ab-lightbox-image>' +
          '<button data-ab-lightbox-next></button>' +
        '</dialog>' +
      '</div>' +
      '<div class="ab-info"><h1 class="ab-title">Test</h1></div>' +
    '</div>'
  );
}

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', reject);
  });
}

async function main() {
  const payload = JSON.parse(await readStdin());
  const code = payload.code;

  const dom = new JSDOM('<!DOCTYPE html><body>' + buildMarkup(5) + '</body>', {
    runScripts: 'outside-only',
    pretendToBeVisual: true,
  });

  // Images are already "loaded" so naturalWidth/Height are available.
  const imgProto = dom.window.HTMLImageElement.prototype;
  Object.defineProperty(imgProto, 'naturalWidth', { get: () => 1600 });
  Object.defineProperty(imgProto, 'naturalHeight', { get: () => 900 });
  Object.defineProperty(imgProto, 'complete', { get: () => true });

  let mutations = 0;
  const RealObserver = dom.window.MutationObserver;
  dom.window.MutationObserver = class extends RealObserver {
    constructor(callback) {
      super((records, observer) => {
        mutations += records.length;
        if (mutations > MAX_MUTATIONS) {
          console.error(
            'FAIL: observer produced ' + mutations + ' mutations (limit ' +
            MAX_MUTATIONS + ') -- infinite feedback loop, page would freeze.'
          );
          process.exit(1);
        }
        callback(records, observer);
      });
    }
  };

  try {
    dom.window.eval(code);
  } catch (err) {
    console.error('FAIL: page script threw: ' + err.message);
    process.exit(1);
  }

  dom.window.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
  dom.window.HTMLDialogElement.prototype.close = function () { this.open = false; };
  const gallery = dom.window.document.querySelector('.ab-photo');
  const lightbox = gallery.querySelector('[data-ab-lightbox]');
  gallery.querySelector('[data-ab-thumb="1"]').click();
  if (!gallery.querySelector('[data-ab-slide="1"]').classList.contains('active')) {
    throw new Error('Selecting a thumbnail did not change the main image');
  }
  if (gallery.querySelector('[data-ab-counter]').textContent !== '2 / 5') {
    throw new Error('The image counter did not update after thumbnail selection');
  }

  gallery.querySelector('[data-ab-open-gallery]').click();
  if (!lightbox.open || !lightbox.querySelector('[data-ab-lightbox-image]').src.endsWith('/p3.png')) {
    throw new Error('The overflow thumbnail did not open the selected image in the gallery');
  }
  dom.window.document.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'ArrowRight' }));
  if (!lightbox.querySelector('[data-ab-lightbox-image]').src.endsWith('/p4.png')) {
    throw new Error('Right-arrow navigation did not advance through all project images');
  }
  lightbox.querySelector('[data-ab-close]').click();
  if (lightbox.open) throw new Error('The close button did not close the lightbox');

  await new Promise((resolve) => setTimeout(resolve, 500));

  if (mutations > MAX_MUTATIONS) {
    console.error('FAIL: runaway MutationObserver (' + mutations + ' mutations)');
    process.exit(1);
  }

  console.log(
    'OK: gallery controls worked and settled after ' + mutations + ' mutations'
  );
  process.exit(0);
}

main().catch((err) => {
  console.error('FAIL: ' + err.stack);
  process.exit(1);
});
