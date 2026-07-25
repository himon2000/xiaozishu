/**
 * 下山历练 - 就业资源详情
 * 路径: pages/opportunity-detail/opportunity-detail
 */
const { get, post, put } = require('../../utils/request');

Page({
  data: {
    id: '',
    opportunity: null,
    loading: true,
    // 申请表单
    showApplyModal: false,
    applyForm: {
      message: '',
      resume_url: '',
    },
    // 申请状态
    isPublisher: false,
    applications: [],
  },

  onLoad(options) {
    if (!options.id) {
      wx.showToast({ title: '参数错误', icon: 'none' });
      wx.navigateBack();
      return;
    }
    this.setData({ id: options.id });
    this.loadDetail();
  },

  onShow() {
    if (this.data.id) {
      this.loadDetail();
    }
  },

  async loadDetail() {
    this.setData({ loading: true });
    try {
      const res = await get(`/opportunities/${this.data.id}`);
      const app = getApp();
      const myOpenid = app.globalData.userInfo?.openid || '';

      this.setData({
        opportunity: res,
        isPublisher: res.publisher?.openid === myOpenid,
        loading: false,
      });

      // 如果是发布者，加载申请列表
      if (this.data.isPublisher) {
        this.loadApplications();
      }
    } catch (e) {
      console.error('加载详情失败', e);
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  // 加载收到的申请
  async loadApplications() {
    try {
      const res = await get(`/opportunities/${this.data.id}/applications`);
      this.setData({ applications: res.applications || [] });
    } catch (e) {
      console.error('加载申请列表失败', e);
    }
  },

  // 收藏/取消收藏
  async onToggleFavorite() {
    const { opportunity } = this.data;
    if (!opportunity) return;

    try {
      const res = await post(`/opportunities/${opportunity.id}/favorite`);
      this.setData({
        'opportunity.is_favorited': res.is_favorited,
        'opportunity.favorite_count': opportunity.favorite_count + (res.is_favorited ? 1 : -1),
      });
      wx.showToast({
        title: res.is_favorited ? '已收藏' : '已取消收藏',
        icon: 'success'
      });
    } catch (e) {
      wx.showToast({ title: e.detail || '操作失败', icon: 'none' });
    }
  },

  // 打开申请弹窗
  onOpenApply() {
    this.setData({ showApplyModal: true });
  },

  // 关闭申请弹窗
  onCloseApply() {
    this.setData({ showApplyModal: false, applyForm: { message: '', resume_url: '' } });
  },

  // 更新申请表单
  onApplyInput(e) {
    const field = e.currentTarget.dataset.field;
    const form = this.data.applyForm;
    form[field] = e.detail.value;
    this.setData({ applyForm: form });
  },

  // 提交申请
  async onSubmitApply() {
    const { applyForm, opportunity } = this.data;
    if (!applyForm.message.trim()) {
      wx.showToast({ title: '请填写申请留言', icon: 'none' });
      return;
    }

    try {
      await post(`/opportunities/${opportunity.id}/apply`, applyForm);
      wx.showToast({ title: '申请成功！', icon: 'success' });
      this.onCloseApply();
      this.loadDetail();
    } catch (e) {
      wx.showToast({ title: e.detail || '申请失败', icon: 'none' });
    }
  },

  // 处理申请（发布者）
  async onHandleApplication(e) {
    const { id, status } = e.currentTarget.dataset;
    const action = status === 'accepted' ? '通过' : '拒绝';

    wx.showModal({
      title: `确认${action}`,
      content: `确定要${action}该申请吗？`,
      success: async (res) => {
        if (res.confirm) {
          try {
            await put(`/opportunities/${this.data.id}/applications/${id}?status=${status}`);
            wx.showToast({ title: `已${action}`, icon: 'success' });
            this.loadApplications();
          } catch (e) {
            wx.showToast({ title: e.detail || '操作失败', icon: 'none' });
          }
        }
      }
    });
  },

  // 查看申请者主页
  onViewProfile(e) {
    const openid = e.currentTarget.dataset.openid;
    wx.navigateTo({ url: `/subpackages/mentor/mentor-apply/mentor-apply?openid=${openid}` });
  },

  // 复制联系方式
  onCopyContact() {
    const { opportunity } = this.data;
    if (opportunity.contact_wx) {
      wx.setClipboardData({
        data: opportunity.contact_wx,
        success: () => {
          wx.showToast({ title: '微信号已复制', icon: 'success' });
        }
      });
    }
  },

  // 复制申请链接
  onCopyUrl() {
    const { opportunity } = this.data;
    if (opportunity.apply_url) {
      wx.setClipboardData({
        data: opportunity.apply_url,
        success: () => {
          wx.showToast({ title: '链接已复制', icon: 'success' });
        }
      });
    }
  },

  // 外部申请
  onExternalApply() {
    const { opportunity } = this.data;
    if (opportunity.apply_url) {
      wx.navigateToMiniProgram({
        appId: '',  // 可配置小程序appid
        path: '',
        extraData: { url: opportunity.apply_url },
        fail: () => {
          // 如果跳转小程序失败，复制链接
          this.onCopyUrl();
        }
      });
    }
  },

  // 删除资源（发布者）
  onDeleteOpportunity() {
    wx.showModal({
      title: '确认删除',
      content: '确定要删除该资源吗？此操作不可撤销！',
      success: async (res) => {
        if (res.confirm) {
          try {
            await post(`/opportunities/${this.data.id}/delete`);  // 用POST模拟DELETE
            wx.showToast({ title: '已删除', icon: 'success' });
            setTimeout(() => {
              wx.navigateBack();
            }, 1500);
          } catch (e) {
            wx.showToast({ title: e.detail || '删除失败', icon: 'none' });
          }
        }
      }
    });
  },

  // 分享
  onShareAppMessage() {
    const { opportunity } = this.data;
    return {
      title: opportunity?.title || '下山历练机会',
      path: `/pages/opportunity-detail/opportunity-detail?id=${this.data.id}`,
    };
  },
});
