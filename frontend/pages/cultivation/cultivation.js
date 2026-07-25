const { get } = require('../../utils/request');

Page({
  data: {
    user: null,
    currentRole: null,
    cultivationLevel: 1,
    cultivationExp: 0,
    cultivationProgress: 0,
    expToNextLevel: 100,

    // 境界列表
    realms: [
      { name: '练气期', icon: '🌱', level: 1, minExp: 0, maxExp: 100 },
      { name: '筑基期', icon: '🧿', level: 2, minExp: 100, maxExp: 300 },
      { name: '金丹期', icon: '🔮', level: 3, minExp: 300, maxExp: 600 },
      { name: '元婴期', icon: '✨', level: 4, minExp: 600, maxExp: 1000 },
      { name: '化神期', icon: '🌟', level: 5, minExp: 1000, maxExp: 1500 },
      { name: '大乘期', icon: '🌙', level: 6, minExp: 1500, maxExp: 2100 },
      { name: '渡劫期', icon: '⚡', level: 7, minExp: 2100, maxExp: 2800 },
      { name: '飞升期', icon: '🚀', level: 8, minExp: 2800, maxExp: 99999 },
    ],

    // 修为记录
    expRecords: [],
  },

  onLoad() {
    this.loadData();
  },

  async loadData() {
    try {
      const userRes = await get('/auth/me').catch(() => null);
      const user = userRes || {};

      const roles = user.roles || [];
      const currentRole = user.current_role_obj || (roles.length > 0 ? roles.find(r => r.enabled) : null);

      const cultivationLevel = user.cultivation_level || 1;
      const cultivationExp = user.cultivation_exp || 0;
      const expNeeded = this.getExpNeededForLevel(cultivationLevel);
      const expToNextLevel = expNeeded - (cultivationExp % expNeeded);
      const cultivationProgress = ((cultivationExp % expNeeded) / expNeeded) * 100;

      // 模拟修为记录
      const expRecords = [
        { type: '完成任务', amount: '+50', time: '今天 14:30', desc: '完成服务：论文润色' },
        { type: '获得好评', amount: '+20', time: '昨天 18:20', desc: '获得5星好评' },
        { type: '邀请好友', amount: '+50', time: '03-15 10:00', desc: '邀请道友注册' },
        { type: '完成任务', amount: '+30', time: '03-14 20:15', desc: '完成需求：代课服务' },
      ];

      this.setData({
        user,
        currentRole,
        cultivationLevel,
        cultivationExp,
        cultivationProgress: cultivationProgress.toFixed(0),
        expToNextLevel,
        expRecords,
      });
    } catch (e) {
      console.error('加载修为数据失败', e);
    }
  },

  getExpNeededForLevel(level) {
    return 100 + (level - 1) * 50;
  },

  onShareAppMessage() {
    return {
      title: `我在小紫薯已达 ${this.data.cultivationLevel} 级修为，快来一起修仙！`,
      path: '/pages/home/home',
    };
  },
});
