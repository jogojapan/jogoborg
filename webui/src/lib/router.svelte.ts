// Minimal hash-based router (works at any base path behind a reverse proxy).

function readPath(): string {
  const h = window.location.hash;
  if (!h || h === '#') return '/login';
  const p = h.replace(/^#/, '');
  return p.startsWith('/') ? p : `/${p}`;
}

export const router = $state({ path: readPath() });

export function navigate(path: string): void {
  if (window.location.hash === `#${path}`) {
    router.path = path;
    return;
  }
  window.location.hash = path;
}

window.addEventListener('hashchange', () => {
  router.path = readPath();
});