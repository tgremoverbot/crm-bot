import { useEffect } from 'react';

export function useContentProtection() {
  useEffect(() => {
    // Block right-click context menu
    const onContextMenu = (e: MouseEvent) => e.preventDefault();

    // Block screenshot/copy/print shortcuts
    const onKeyDown = (e: KeyboardEvent) => {
      const ctrl = e.ctrlKey || e.metaKey;
      if (
        (ctrl && e.key === 'p') ||  // print
        (ctrl && e.key === 's') ||  // save
        (ctrl && e.key === 'u') ||  // view source
        (ctrl && e.key === 'c') ||  // copy
        (ctrl && e.key === 'a') ||  // select all
        e.key === 'PrintScreen'     // PrtSc (limited effect)
      ) {
        e.preventDefault();
      }
    };

    // Blur the page when user switches away (e.g. to screenshot tool)
    const onVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        // intentionally blank — just a hook point
      }
    };

    document.addEventListener('contextmenu', onContextMenu);
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      document.removeEventListener('contextmenu', onContextMenu);
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, []);
}
