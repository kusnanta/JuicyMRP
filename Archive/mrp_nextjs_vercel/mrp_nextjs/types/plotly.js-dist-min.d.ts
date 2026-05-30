// Minimal type declaration for plotly.js-dist-min
// Using a self-contained definition avoids dependency on @types/plotly.js
declare module 'plotly.js-dist-min' {
  interface Layout {
    [key: string]: unknown
  }
  interface Config {
    [key: string]: unknown
  }
  function react(
    root: HTMLElement | string,
    data: object[],
    layout?: Partial<Layout>,
    config?: Partial<Config>,
  ): Promise<void>
  function newPlot(
    root: HTMLElement | string,
    data: object[],
    layout?: Partial<Layout>,
    config?: Partial<Config>,
  ): Promise<void>
}
