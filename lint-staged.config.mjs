export default {
  // Lint & auto-fix staged TS/JS/TSX in the FE workspace
  '*.{js,jsx,ts,tsx}': () => 'npm run -w frontend lint -- --fix',

  // Format docs / metadata
  '*.{json,yml,md}': 'npx prettier --write',

  // Format backend Python on changed files (optional)
  '*.py': 'python -m black'
};
