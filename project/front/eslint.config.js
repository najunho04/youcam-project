// 슬라이스 간 import 차단 (make lint). 수정 금지.
import { readdirSync } from 'node:fs'
import javascript from '@eslint/js'
import typescript from 'typescript-eslint'
import importPlugin from 'eslint-plugin-import-x'
import { createTypeScriptImportResolver } from 'eslint-import-resolver-typescript'

const featureNames = readdirSync('./src/feature', { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)

const sliceZones = featureNames.map((name) => ({
  target: `./src/feature/${name}`,
  from: './src/feature',
  except: [`./${name}`],
  message: '다른 슬라이스는 import 할 수 없습니다. common/ 과 shared/ 만 의존하세요.',
}))

export default typescript.config(
  { ignores: ['dist', 'node_modules'] },
  javascript.configs.recommended,
  ...typescript.configs.recommended,
  {
    files: ['src/**/*.{ts,tsx}'],
    plugins: { 'import-x': importPlugin },
    settings: { 'import-x/resolver-next': [createTypeScriptImportResolver()] },
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/ban-ts-comment': 'error',
      'import-x/no-restricted-paths': [
        'error',
        {
          zones: [
            ...sliceZones,
            { target: './src/common', from: ['./src/feature', './src/shared', './src/app'], message: 'common 은 타입만 둡니다.' },
            { target: './src/shared', from: ['./src/feature', './src/app'], message: 'shared 는 feature 를 import 할 수 없습니다.' },
          ],
        },
      ],
    },
  },
)
