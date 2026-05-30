/// <reference types="plotly.js" />

// plotly.js-dist-min is a pre-bundled UMD build with the same API surface.
// We re-export all types from @types/plotly.js so TypeScript is satisfied.
declare module 'plotly.js-dist-min' {
  import * as Plotly from 'plotly.js'
  export = Plotly
}
