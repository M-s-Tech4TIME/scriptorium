import js from "@eslint/js";
import globals from "globals";

// TypeScript is checked by `tsc --noEmit`; typescript-eslint currently
// declares `typescript <6.1`, so it cannot lint the pinned TS 7 compiler.
// Keep ESLint on JavaScript/config files until that upstream peer range moves.
export default [
  {
    ignores: ["dist/", "node_modules/", "src/**/*.ts", "src/**/*.tsx"],
  },
  js.configs.recommended,
  {
    files: ["**/*.{js,mjs,cjs}"],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
  },
];
