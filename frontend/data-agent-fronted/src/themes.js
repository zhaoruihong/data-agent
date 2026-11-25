export const themes = [
  {
    key: 'aurora',
    name: '极光深空',
    desc: '深蓝紫底 + 极光流动光斑，科技感拉满',
    swatch: ['#6366f1', '#22d3ee', '#a855f7'],
  },
  {
    key: 'glass-light',
    name: '晨曦玻璃',
    desc: '浅白底 + 柔和彩色光斑 + 毛玻璃卡片',
    swatch: ['#a5b4fc', '#f9a8d4', '#fcd34d'],
  },
  {
    key: 'cyberpunk',
    name: '霓虹夜城',
    desc: '纯黑底 + 高饱和霓虹青/品红/黄 + 扫描线',
    swatch: ['#00f0ff', '#ff2e97', '#ffe600'],
  },
  {
    key: 'sunset',
    name: '暮色暖洋',
    desc: '深棕紫渐变 + 橙红粉暖色，温暖舒适',
    swatch: ['#ff6b6b', '#feca57', '#ff9ff3'],
  },
  {
    key: 'ocean',
    name: '薄荷深海',
    desc: '深蓝绿 + 青绿渐变，清新通透',
    swatch: ['#0ea5e9', '#34d399', '#2dd4bf'],
  },
  {
    key: 'paper',
    name: '墨韵纸张',
    desc: '米白纸张底 + 墨黑文字 + 细金线，极简克制',
    swatch: ['#c9a961', '#1c1917', '#f5f1e8'],
  },
];

export const defaultThemeKey = 'aurora';

export function isValidTheme(key) {
  return themes.some((t) => t.key === key);
}