const { get } = require('../../utils/request');

Page({
  data: {
    user: null,

    // 资产数据
    assets: {
      lingshi: 588,
      frozen: 100,
      total: 688,
    },

    // 交易记录
    transactions: [],

    // 充值套餐
    packages: [
      { id: 1, amount: 50, price: 5, bonus: 0, desc: '50灵石' },
      { id: 2, amount: 100, price: 9.9, bonus: 10, desc: '100灵石+10' },
      { id: 3, amount: 200, price: 18.8, bonus: 30, desc: '200灵石+30' },
      { id: 4, amount: 500, price: 45, bonus: 100, desc: '500灵石+100' },
    ],

    // VIP套餐
    vipPackages: [
      { id: 1, name: '月度会员', price: 30, duration: '30天', benefits: ['置顶服务', '专属标识', '优先推荐'] },
      { id: 2, name: '季度会员', price: 80, duration: '90天', benefits: ['置顶服务', '专属标识', '优先推荐', '9折优惠'] },
    ],

    currentTab: 'detail',
  },

  onLoad() {
    this.loadData();
  },

  async loadData() {
    try {
      const userRes = await get('/auth/me').catch(() => null);
      const user = userRes || {};

      // 交易流水接口尚未开放，不能用演示数据冒充真实记录。
      const transactions = [];

      const lingshi = Number(user.lingshi ?? user.spirit_stones ?? 0);
      const frozen = Number(user.frozen_lingshi ?? user.spirit_stones_frozen ?? 0);
      const assets = {
        lingshi,
        frozen,
        total: lingshi + frozen,
      };

      this.setData({
        user,
        assets,
        transactions,
      });
    } catch (e) {
      console.error('加载资产数据失败', e);
    }
  },

  onTabChange(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ currentTab: tab });
  },

  onRecharge() {
    wx.showToast({ title: '充值功能开发中', icon: 'none' });
  },

  onWithdraw() {
    wx.showToast({ title: '提现功能开发中', icon: 'none' });
  },

  onBuyPackage(e) {
    const pkg = e.currentTarget.dataset.pkg;
    wx.showModal({
      title: '确认充值',
      content: `确认充值 ${pkg.desc} 灵石，支付 ¥${pkg.price}？`,
      success: (res) => {
        if (res.confirm) {
          wx.showToast({ title: '支付功能开发中', icon: 'none' });
        }
      },
    });
  },

  onBuyVip(e) {
    const pkg = e.currentTarget.dataset.pkg;
    wx.showModal({
      title: '开通会员',
      content: `确认开通 ${pkg.name}，支付 ¥${pkg.price}？`,
      success: (res) => {
        if (res.confirm) {
          wx.showToast({ title: '支付功能开发中', icon: 'none' });
        }
      },
    });
  },

  onShareAppMessage() {
    return {
      title: '查看我的资产，灵石多多！',
      path: '/pages/home/home',
    };
  },
});
