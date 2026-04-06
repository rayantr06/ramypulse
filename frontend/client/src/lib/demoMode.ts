export const DEMO_MODE = true;

export function demoDisabledProps(label: string) {
  if (!DEMO_MODE) {
    return {};
  }

  return {
    "aria-disabled": true,
    "data-demo-disabled": label,
    tabIndex: -1 as const,
  };
}
