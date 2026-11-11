/* Nombre funcional existente; nombre comercial definitivo (TBD). */
(() => {
  const BRAND_NAME = 'Turnos odontologia';
  const bindBrand = () => {
    document.querySelectorAll('[data-brand-name]').forEach((node) => {
      node.textContent = BRAND_NAME;
    });
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindBrand, { once: true });
  } else {
    bindBrand();
  }
})();
