/**
 * 格式化工具
 */

/**
 * 金额格式化（分 → 元）
 * 用于：分红池、充值价格、真实货币显示
 */
function formatPrice(fen, showSymbol = true) {
  if (fen == null) return '0.00';
  const yuan = (fen / 100).toFixed(2);
  return showSymbol ? `¥${yuan}` : yuan;
}

/**
 * 灵石格式化（数字 → 灵石显示）
 * 用于：服务价格、订单价格
 * 100 灵石 = 1 元（100分）
 * 后端传 fen，前端显示为 stones = fen
 */
function formatLingShi(fen, showUnit = true) {
  if (fen == null) return '0';
  const stones = Math.round(fen); // fen 直接作为灵石数（分=灵石）
  return showUnit ? `${stones}灵石` : stones;
}

/**
 * 灵石数字格式化（带分隔符）
 */
function formatLingShiNumber(fen) {
  if (fen == null) return '0';
  const stones = Math.round(fen);
  return stones.toLocaleString('zh-CN');
}

/**
 * 境界名称
 */
const LEVEL_NAMES = {
  1: '炼气期', 2: '筑基期', 3: '金丹期', 4: '元婴期', 5: '化神期',
};
const LEVEL_COLORS = {
  1: '#999999', 2: '#00cc44', 3: '#4499ff', 4: '#cc44ff', 5: '#ffd700',
};
const LEVEL_ICONS = {
  1: '🌫', 2: '🌿', 3: '💙', 4: '💜', 5: '⭐',
};

function formatLevel(level) {
  return LEVEL_NAMES[level] || '炼气期';
}

function formatLevelColor(level) {
  return LEVEL_COLORS[level] || '#999999';
}

function formatLevelIcon(level) {
  return LEVEL_ICONS[level] || '🌫';
}

/**
 * 道法类型名称
 */
const DAOFA_NAMES = {
  chuan_gong: '传功授法',
  mi_jing: '联袂问道',
  zong_men: '万宗宝鉴',
  xia_shan: '下山历练',
  zhi_fa: '天衡裁决',
  cang_jing: '道藏天阁',
};
const DAOFA_ICONS = {
  chuan_gong: '📚',
  mi_jing: '🔬',
  zong_men: '🏫',
  xia_shan: '💼',
  zhi_fa: '⚙️',
  cang_jing: '📖',
};

function formatDaoFa(name) {
  return DAOFA_NAMES[name] || name;
}

function formatDaoFaIcon(name) {
  return DAOFA_ICONS[name] || '📜';
}

/**
 * 日期格式化
 */
function formatDate(timestamp) {
  if (!timestamp) return '';
  const d = new Date(timestamp);
  const now = new Date();
  const diff = now - d;

  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;

  return `${d.getMonth() + 1}月${d.getDate()}日`;
}

function formatDateTime(timestamp) {
  if (!timestamp) return '';
  const d = new Date(timestamp);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

/**
 * 手机号脱敏
 */
function maskPhone(phone) {
  if (!phone || phone.length !== 11) return phone;
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2');
}

/**
 * 星级评分渲染
 */
function renderStars(rating) {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  return '★'.repeat(full) + (half ? '½' : '') + '☆'.repeat(5 - full - (half ? 1 : 0));
}

module.exports = {
  formatPrice,
  formatLingShi,
  formatLingShiNumber,
  formatLevel,
  formatLevelColor,
  formatLevelIcon,
  formatDaoFa,
  formatDaoFaIcon,
  formatDate,
  formatDateTime,
  maskPhone,
  renderStars,
  LEVEL_NAMES,
  LEVEL_COLORS,
  LEVEL_ICONS,
  DAOFA_NAMES,
  DAOFA_ICONS,
};
