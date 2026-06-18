// Flat config для ESLint 9 + eslint-config-next 16 (пакет экспортирует готовый массив).
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypeScript from "eslint-config-next/typescript";

const eslintConfig = [
  ...nextCoreWebVitals,
  ...nextTypeScript,
  {
    ignores: [".next/**", "node_modules/**"],
  },
];

export default eslintConfig;
