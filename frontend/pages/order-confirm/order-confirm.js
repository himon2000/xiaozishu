const { get, post } = require('../../utils/request');

Page({
  data: {
    serviceInfo: null,
    orderForm: {
      sessions: 1,
      message: '',
    },
    totalPrice: 0,
    submitting: false,
  },

  onLoad(options) {
    const serviceId = options.service_id || options.id;
    if (serviceId) {
      this.loadServiceInfo(serviceId);
    }
  },

  async loadServiceInfo(serviceId) {
    try {
      const serviceInfo = await get(`/services/${serviceId}`);
      const pricing = serviceInfo.pricing || {};
      const provider = serviceInfo.provider || {};
      const minSessions = pricing.min_sessions || serviceInfo.min_sessions || 1;
      const price = pricing.price || serviceInfo.price || 0;
      this.setData({
        serviceInfo: { ...serviceInfo, pricing, provider },
        'orderForm.sessions': minSessions,
        totalPrice: price * minSessions,
      });
    } catch (err) {
      console.error('[order-confirm] load service failed:', err);
      wx.showToast({ title: err.message || '服务加载失败', icon: 'none' });
    }
  },

  onQuantityChange(e) {
    const minSessions = this.data.serviceInfo?.pricing?.min_sessions || this.data.serviceInfo?.min_sessions || 1;
    const sessions = Math.max(parseInt(e.detail.value, 10) || minSessions, minSessions);
    const price = this.data.serviceInfo?.pricing?.price || this.data.serviceInfo?.price || 0;
    this.setData({
      'orderForm.sessions': sessions,
      totalPrice: price * sessions,
    });
  },

  onMessageInput(e) {
    this.setData({ 'orderForm.message': e.detail.value });
  },

  async onConfirmOrder() {
    if (this.data.submitting) return;
    const serviceInfo = this.data.serviceInfo;
    if (!serviceInfo) {
      wx.showToast({ title: '服务信息加载中', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });
    try {
      const order = await post('/orders', {
        service_id: serviceInfo.id,
        sessions: this.data.orderForm.sessions,
      });

      wx.showToast({ title: '下单成功', icon: 'success' });
      setTimeout(() => {
        wx.navigateTo({ url: `/pages/order-detail/order-detail?id=${order.id}` });
      }, 800);
    } catch (err) {
      wx.showToast({ title: err.message || '下单失败', icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
