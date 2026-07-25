/**
 * 分红池页面（宗门宝库）
 * 路径：pages/dividend-pool/dividend-pool
 */
const { get, post } = require('../../utils/request');
const app = getApp();

Page({
  data: {
    year: new Date().getFullYear(),
    poolInfo: null,
    eligibleList: [],
    myInfo: null,
    loading: true,
    claiming: false,
  },

  onLoad(options) {
    if (options.year) {
      this.setData({ year: parseInt(options.year) });
    }
    this.loadDividendPool();
  },

  async onShow() {
    await this.loadDividendPool();
  },

  async loadDividendPool() {
    this.setData({ loading: true });
    try {
      const res = await get(`/level/dividend-pool?year=${this.data.year}`);
      this.setData({
        poolInfo: res,
        eligibleList: res.eligible_list || [],
        myInfo: res.your_info,
        loading: false,
      });
    } catch (e) {
      console.error('加载分红池失败', e);
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  onPrevYear() {
    const year = this.data.year - 1;
    this.setData({ year });
    this.loadDividendPool();
  },

  onNextYear() {
    const year = this.data.year + 1;
    if (year > new Date().getFullYear()) {
      wx.showToast({ title: '未来年份不可查看', icon: 'none' });
      return;
    }
    this.setData({ year });
    this.loadDividendPool();
  },

  async onClaimDividend() {
    if (this.data.claiming) return;

    const myInfo = this.data.myInfo;
    if (!myInfo || !myInfo.eligible) {
      wx.showToast({ title: '您暂不符合领取条件', icon: 'none' });
      return;
    }

    this.setData({ claiming: true });

    wx.showModal({
      title: '确认领取',
      content: `确认领取 ${this.data.year} 年度分红 ${myInfo.estimated_share_yuan || 0} 元？`,
      success: async (res) => {
        if (res.confirm) {
          try {
            const result = await post(`/level/dividend-pool/claim?year=${this.data.year}`);
            if (result.success) {
              wx.showModal({
                title: '领取成功',
                content: result.message,
                showCancel: false,
              });
              this.loadDividendPool();
            } else {
              wx.showToast({ title: result.message || '领取失败', icon: 'none' });
            }
          } catch (e) {
            wx.showToast({ title: '领取失败', icon: 'none' });
          }
        }
        this.setData({ claiming: false });
      },
    });
  },

  onEligibleTap(e) {
    const { openid } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/service-detail/service-detail?provider=${openid}`,
    });
  },

  onRefresh() {
    this.loadDividendPool();
  },

  onShareAppMessage() {
    return {
      title: `驯龙阁 ${this.data.year} 年度宗门分红池公示`,
      path: `/pages/dividend-pool/dividend-pool?year=${this.data.year}`,
    };
  },
});
