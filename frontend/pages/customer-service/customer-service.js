// pages/customer-service/customer-service.js - 我的客服
Page({
  data: {
    expandedIndex: -1,
    feedbackText: '',
    faqList: [
      {
        id: 1,
        q: '如何充值灵石？',
        a: '进入「我的」→「我的灵石」，点击充值按钮即可。目前支持微信支付，100灵石 = 1元。',
      },
      {
        id: 2,
        q: '如何发布服务？',
        a: '进入服务广场页面，点击右上角的发布按钮，选择服务类型并填写详细信息后提交。',
      },
      {
        id: 3,
        q: '如何成为导师（大虾/长老）？',
        a: '在「我的角色」中完成角色认证，通过审核后即可成为导师，开始招收弟子。',
      },
      {
        id: 4,
        q: '订单出现问题怎么办？',
        a: '进入「我的灵契」找到对应订单，点击进入详情页后可申请售后或联系客服处理。',
      },
      {
        id: 5,
        q: '推荐码（飞花令）怎么用？',
        a: '在「我的飞花令」中分享你的推荐码给好友，好友注册后双方均可获得灵石奖励。',
      },
    ],
  },

  // ========== 在线客服 ==========

  onOnlineService() {
    // 尝试使用微信客服消息能力
    wx.showToast({ title: '功能开发中，敬请期待', icon: 'none' });
  },

  // ========== 复制邮箱 ==========

  onCopyEmail() {
    wx.setClipboardData({
      data: 'support@xiaozishu.com',
      success: () => {
        wx.showToast({ title: '邮箱已复制', icon: 'success' });
      },
    });
  },

  // ========== FAQ 手风琴 ==========

  onFaqTap(e) {
    const { index } = e.currentTarget.dataset;
    const { expandedIndex } = this.data;
    this.setData({
      expandedIndex: expandedIndex === index ? -1 : index,
    });
  },

  // ========== 意见反馈 ==========

  onFeedbackInput(e) {
    this.setData({ feedbackText: e.detail.value });
  },

  onSubmitFeedback() {
    const { feedbackText } = this.data;
    if (!feedbackText.trim()) {
      wx.showToast({ title: '请输入反馈内容', icon: 'none' });
      return;
    }
    wx.showLoading({ title: '提交中...' });
    setTimeout(() => {
      wx.hideLoading();
      wx.showToast({ title: '提交成功，感谢反馈！', icon: 'success' });
      this.setData({ feedbackText: '' });
    }, 300);
  },
});
