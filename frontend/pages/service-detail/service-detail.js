/**
 * 服务详情页
 * 路径：pages/service-detail/service-detail
 */
const { get, post } = require('../../utils/request');
const { requestPayment } = require('../../utils/payment');

Page({
  data: {
    service: null,
    provider: null,
    sessions: 1,
    totalFee: 0,
    loading: true,
    reviewStats: null,
  },

  onLoad(options) {
    if (options.service_id) {
      this.loadService(options.service_id);
    } else if (options.provider) {
      this.loadProvider(options.provider);
    }
  },

  async loadService(serviceId) {
    try {
      const data = await get(`/services/${serviceId}`);
      // 补充默认信任数据
      const provider = data.provider || {};
      if (provider && !provider.reply_rate) {
        provider.reply_rate = 95; // 默认回复率
      }
      if (provider && !provider.on_time_rate) {
        provider.on_time_rate = 90; // 默认准时率
      }
      this.setData({
        service: data,
        provider,
        sessions: data.pricing?.min_sessions || 1,
        loading: false,
      });
      this.calcTotal();
      // 加载评价统计
      this.loadReviewStats(serviceId);
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  async loadReviewStats(serviceId) {
    try {
      const res = await get(`/reviews/stats/service/${serviceId}`);
      this.setData({ reviewStats: res });
    } catch (e) {
      console.error('加载评价统计失败', e);
    }
  },

  // 查看全部评价
  onViewReviews() {
    const { service } = this.data;
    if (service) {
      wx.navigateTo({
        url: `/pages/review-list/review-list?service_id=${service.id}&title=${encodeURIComponent(service.title)}`,
      });
    }
  },

  async loadProvider(openid) {
    try {
      const data = await get(`/services/provider/${openid}`);
      const provider = data.provider || {};
      if (provider && !provider.reply_rate) {
        provider.reply_rate = 95;
      }
      if (provider && !provider.on_time_rate) {
        provider.on_time_rate = 90;
      }
      this.setData({ provider, loading: false });
    } catch (e) {
      this.setData({ loading: false });
    }
  },

  calcTotal() {
    const { service, sessions } = this.data;
    if (!service) return;
    this.setData({ totalFee: service.pricing.price * sessions });
  },

  onSessionsChange(e) {
    const delta = parseInt(e.currentTarget.dataset.delta);
    const sessions = Math.max((this.data.sessions || 1) + delta, this.data.service?.pricing?.min_sessions || 1);
    this.setData({ sessions });
    this.calcTotal();
  },

  // 查看师傅主页
  onViewMentorProfile() {
    const { provider } = this.data;
    if (provider && provider.openid) {
      wx.navigateTo({
        url: `/subpackages/mentor/mentor-apply/mentor-apply?openid=${provider.openid}`,
      });
    }
  },

  async onBook() {
    const { service, sessions } = this.data;
    if (!service) return;

    wx.showLoading({ title: '灵契签订中...' });
    try {
      const order = await post('/orders', {
        service_id: service.id,
        sessions,
      });
      wx.hideLoading();

      // 调起支付
      const result = await requestPayment(order.id);
      if (result.success) {
        wx.showToast({ title: '支付成功！灵契已签订', icon: 'success' });
        setTimeout(() => {
          wx.navigateTo({ url: `/pages/order-detail/order-detail?order_id=${order.id}` });
        }, 1500);
      } else if (result.reason === 'cancelled') {
        wx.showToast({ title: '支付已取消', icon: 'none' });
      } else {
        wx.showToast({ title: '支付失败', icon: 'none' });
      }
    } catch (e) {
      wx.hideLoading();
      wx.showToast({ title: e.message || '下单失败', icon: 'none' });
    }
  },

  onShareAppMessage() {
    const { service } = this.data;
    return {
      title: service?.title || '来看看这个服务',
      path: `/pages/service-detail/service-detail?service_id=${service?.id}`,
    };
  },
});
