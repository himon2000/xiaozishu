/**
 * 天衡裁决申请页面
 * 路径：pages/dispute-apply/dispute-apply
 */
const { post } = require('../../utils/request');

Page({
  data: {
    orderId: '',
    userRole: 'seeker',
    submitting: false,
    formData: {
      dispute_type: '',
      description: '',
      evidence_images: [],
      expected_action: '',
    },
    disputeTypes: [
      { id: 'quality', label: '📜 传法有瑕', sub: '(服务质量问题)' },
      { id: 'delay', label: '⏰ 逾时未竟', sub: '(超时未完成)' },
      { id: 'attitude', label: '😤 道心不正', sub: '(态度问题)' },
      { id: 'refund', label: '💰 灵石纷争', sub: '(退款争议)' },
      { id: 'cheating', label: '⚠️ 欺心背道', sub: '(作弊/欺诈)' },
      { id: 'other', label: '❓ 其他', sub: '(其他问题)' },
    ],
  },

  onLoad(options) {
    if (options.order_id) {
      this.setData({ orderId: options.order_id });
    }
    if (options.user_role) {
      this.setData({ userRole: options.user_role });
    }
  },

  onSelectType(e) {
    const { type } = e.currentTarget.dataset;
    this.setData({
      'formData.dispute_type': type
    });
  },

  onDescriptionInput(e) {
    this.setData({
      'formData.description': e.detail.value
    });
  },

  onSelectAction(e) {
    const { action } = e.currentTarget.dataset;
    this.setData({
      'formData.expected_action': action
    });
  },

  onChooseImage() {
    wx.chooseMedia({
      count: 3 - this.data.formData.evidence_images.length,
      mediaType: ['image'],
      success: (res) => {
        const images = res.tempFiles.map(item => item.tempFilePath);
        this.setData({
          'formData.evidence_images': [...this.data.formData.evidence_images, ...images]
        });
      }
    });
  },

  onRemoveImage(e) {
    const { index } = e.currentTarget.dataset;
    const images = [...this.data.formData.evidence_images];
    images.splice(index, 1);
    this.setData({
      'formData.evidence_images': images
    });
  },

  async onSubmit() {
    const { formData, orderId } = this.data;

    // 验证必填项
    if (!formData.dispute_type) {
      wx.showToast({ title: '请选择问题类型', icon: 'none' });
      return;
    }
    if (!formData.description || formData.description.length < 10) {
      wx.showToast({ title: '请详细描述问题（至少10个字）', icon: 'none' });
      return;
    }
    if (!formData.expected_action) {
      wx.showToast({ title: '请选择期望处理方式', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });

    try {
      // TODO: 上传图片获取URL
      const evidenceUrls = formData.evidence_images;

      await post('/disputes', {
        order_id: orderId,
        dispute_type: formData.dispute_type,
        description: formData.description,
        evidence_images: evidenceUrls,
        expected_action: formData.expected_action,
        user_role: this.data.userRole,
      });

      wx.showToast({ title: '仲裁申请已提交', icon: 'success' });
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
    } catch (e) {
      wx.showToast({ title: e.message || '提交失败', icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
