import resolve from "@rollup/plugin-node-resolve";
import commonjs from "@rollup/plugin-commonjs";
import typescript from "rollup-plugin-typescript2";
import { terser } from "rollup-plugin-terser";
import json from "@rollup/plugin-json";
import { babel } from "@rollup/plugin-babel";

const dev = process.env.ROLLUP_WATCH;

export default [
  {
    input: "js/main.ts",
    output: {
      file: "custom_components/HomeAIVision/homeaivision_panel.js",
      format: "es",
      sourcemap: true,
    },
    plugins: [
      resolve(),
      commonjs(),
      json(),
      typescript(),
      babel({
        exclude: "node_modules/**",
        babelHelpers: "bundled"
      }),
      !dev && terser({ format: { comments: false } }),
    ],
  },
];
