/**
 * 订单详情
 * 路径：pages/order-detail/order-detail
 */
const { get, patch, post } = require('../../utils/request');

Page({
  data: {
    order: null,
    loading: true,
    userRole: 'seeker',
    hasReviewed: false,
    disputeTypes: [
      { id: 'not_on_time', label: '服务者未按时完成' },
      { id: 'quality_issue', label: '服务质量不达标' },
      { id: 'attitude_issue', label: '沟通态度问题' },
      { id: 'other', label: '其他问题' },
    ],
  },

  onLoad(options) {
    if (options.order_id) {
      this.loadOrder(options.order_id);
    }
    const userInfo = getApp().globalData.userInfo;
    this.setData({ userRole: userInfo?.role || 'seeker' });
  },

  async loadOrder(orderId) {
    try {
      const order = await get(`/orders/${orderId}`);
      // 检查是否已评价
      if (order.review_id) {
        this.setData({ hasReviewed: true });
      }
      this.setData({ order, loading: false });
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  // 跳转到评价页面
  onGoReview() {
    const { order } = this.data;
    wx.navigateTo({
      url: `/pages/review/review?order_id=${order.id}&title=${encodeURIComponent(order.service_snapshot.title)}&provider=${encodeURIComponent(order.provider?.nickname || '')}`,
    });
  },

  async onStatusUpdate(e) {
    const { status, remark } = e.currentTarget.dataset;
    const { order } = this.data;
    wx.showLoading({ title: '处理中...' });
    try {
      await patch(`/orders/${order.id}/status`, { status, remark });
      wx.showToast({ title: '更新成功', icon: 'success' });
      this.loadOrder(order.id);
    } catch (e) {
      wx.showToast({ title: e.message || '更新失败', icon: 'none' });
    } finally {
      wx.hideLoading();
    }
  },

  onApplyDispute() {
    const { order } = this.data;
    const isSeeker = this.data.userRole === 'seeker';

    wx.showModal({
      title: '申请仲裁',
      content: '确定要申请平台仲裁吗？\n\n我们将介入调查并公正处理。如仲裁成功，将根据情况退款。',
      confirmText: '确定申请',
      cancelText: '再想想',
      success: async (res) => {
        if (res.confirm) {
          // 跳转到仲裁申请页面
          wx.navigateTo({
            url: `/pages/dispute-apply/dispute-apply?order_id=${order.id}&user_role=${isSeeker ? 'seeker' : 'provider'}`
          });
        }
      }
    });
  },
});
