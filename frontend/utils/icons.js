/**
 * 修仙风格图标配置
 * 小紫薯 · 明明相代校园接力平台
 *
 * 命名规范：
 * - 修仙标签：使用修仙术语
 * - 原标签旁注：使用 (原标签) 格式作为补充说明
 */

module.exports = {
  // 道法分类图标映射（修仙风格 + 原标签旁注）
  daoFaIcons: {
    'chuan_gong': '📚',   // 传功授法（学科辅导）
    'mi_jing': '🔬',      // 联袂问道（科研组队）
    'zong_men': '🏫',     // 万宗宝鉴（志愿咨询）
    'xia_shan': '💼',     // 下山历练（实习就业）
    'zhi_fa': '⚙️',       // 天衡裁决（客服仲裁）
    'cang_jing': '📖',   // 道藏天阁（资源社区）
  },

  // 道法分类完整配置
  daoFaCategories: [
    { id: 'chuan_gong', name: '传功授法', sub: '学科辅导/竞赛指导', icon: '📚' },
    { id: 'mi_jing',    name: '联袂问道', sub: '课题带教/科研组队', icon: '🔬' },
    { id: 'zong_men',   name: '万宗宝鉴', sub: '志愿咨询/名校攻略', icon: '🏫' },
    { id: 'xia_shan',   name: '下山历练', sub: '实习内推/名企就业', icon: '💼' },
    { id: 'zhi_fa',     name: '天衡裁决', sub: '纠纷仲裁/客服支持', icon: '⚙️' },
    { id: 'cang_jing',  name: '道藏天阁', sub: '学习笔记/经验攻略', icon: '📖' },
  ],

  // 模块图标
  moduleIcons: {
    // TabBar（修仙命名 + 原标签旁注）
    '道籍玉牒': '🏠',      // 首页/用户模块
    '万务仙坊': '🛒',      // 服务广场
    '灵契法帖': '📋',      // 订单模块
    '个人': '👤',          // 个人中心

    // 个人中心菜单（修仙命名 + 原标签旁注）
    '我的服务': '📜',      // (发布)
    '灵契法帖': '📋',      // (订单)
    '联袂问道': '🎯',      // (组队)
    '寻访大师': '🐲',      // (导师)
    '我的学员': '🎓',      // (导师)
    '修为境界': '⚡',      // (等级)
    '均利道池': '💰',      // (分红)
    '道藏天阁': '📖',      // (资源)
    '万宗宝鉴': '🏫',      // (百科)
    '我的发布': '✍️',      // (内容)
    '我的收藏': '⭐',      // (收藏)
    '身份认证': '🏅',      // (实名)
  },

  // 信任认证标签（修仙标签 + 原标签旁注）
  trustBadges: {
    realCert: { name: '灵根', sub: '(实名认证)', icon: '✓' },
    schoolCert: { name: '宗门', sub: '(校园认证)', icon: '🎓' },
    goldBadge: { name: '金丹', sub: '(金牌服务)', icon: '🏆' },
    fastReply: { name: '秒回', sub: '(极速回复)', icon: '⚡' },
  },

  // 订单状态（修仙状态 + 原状态旁注）
  orderStatus: {
    pending_payment: { name: '待付灵石', sub: '(待支付)', color: '#ffa502' },
    paid:             { name: '已付灵石', sub: '(已支付)', color: '#00d4ff' },
    assigned:         { name: '已接单', sub: '(已接单)', color: '#00d4ff' },
    in_progress:      { name: '修炼中', sub: '(进行中)', color: '#cc44ff' },
    pending_confirm:   { name: '待验收', sub: '(待确认)', color: '#ffa502' },
    completed:        { name: '已完成', sub: '(已完成)', color: '#2ed573' },
    dispute:          { name: '纠纷中', sub: '(纠纷中)', color: '#ff4757' },
    cancelled:        { name: '已废弃', sub: '(已取消)', color: '#999' },
  },

  // 组队状态（修仙状态 + 原状态旁注）
  teamStatus: {
    recruiting:   { name: '🔥 招募中', sub: '(招募中)' },
    full:         { name: '✅ 已满员', sub: '(已满)' },
    in_progress:  { name: '🚀 进行中', sub: '(进行中)' },
    completed:    { name: '🏁 已结束', sub: '(已结束)' },
  },

  // 仲裁类型（修仙风格 + 原类型旁注）
  disputeTypes: [
    { id: 'quality', label: '📜 传法有瑕', sub: '(服务质量问题)' },
    { id: 'delay', label: '⏰ 逾时未竟', sub: '(超时未完成)' },
    { id: 'attitude', label: '😤 道心不正', sub: '(态度问题)' },
    { id: 'refund', label: '💰 灵石纷争', sub: '(退款争议)' },
    { id: 'cheating', label: '⚠️ 欺心背道', sub: '(作弊/欺诈)' },
    { id: 'other', label: '❓ 其他', sub: '(其他问题)' },
  ],

  // 境界名称
  levelNames: {
    1: '炼气期',
    2: '筑基期',
    3: '金丹期',
    4: '元婴期',
    5: '化神期',
    6: '大乘期',
    7: '渡劫期',
  },

  // 组队分类（修仙风格 + 原分类旁注）
  teamCategories: [
    { id: 'mi_jing', name: '联袂问道', sub: '(课题/科研)', icon: '🔬' },
    { id: 'competition', name: '问道竞技', sub: '(竞赛组队)', icon: '🏆' },
    { id: 'project', name: '共谋大事', sub: '(项目合作)', icon: '💡' },
    { id: 'study', name: '同修共进', sub: '(学习小组)', icon: '📚' },
  ],

  // 订单视角标签
  orderViewTabs: [
    { key: 'seeker', label: '👤 求道者视角' },
    { key: 'provider', label: '📜 传法者视角' },
  ],

  // 我的组队视角标签
  myTeamsTabs: [
    { key: 'created', label: '🔱 我发起的' },
    { key: 'joined', label: '🤝 我加入的' },
  ],

  // 服务保障文案
  guaranteeText: `
🛡️ 天道契约保障

🔒 灵契托管：灵石暂存天道，圆满后放款
📞 天衡裁决：纠纷提交，48小时内裁断
⚖️ 7x24小时值守，有问必答
  `,
};
