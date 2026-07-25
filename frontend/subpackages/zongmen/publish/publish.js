/**
 * 万宗宝鉴 - 发布咨询需求
 * 路径：subpackages/zongmen/publish/publish
 */
const { post, get } = require('../../../utils/request');

Page({
  data: {
    // 咨询类型
    consultTypes: [
      { id: 'volunteer', name: '志愿填报', icon: '🎯' },
      { id: 'school', name: '院校选择', icon: '🏫' },
      { id: 'major', name: '专业方向', icon: '📖' },
      { id: 'strategy', name: '备考策略', icon: '📚' },
    ],
    // 目标层次
    targetTiers: [
      { id: 'top', name: '顶尖985' },
      { id: '985', name: '普通985' },
      { id: '211', name: '211院校' },
      { id: 'pass', name: '一本院校' },
    ],
    // 当前选中的值
    consultType: '',
    targetTier: '',
    title: '',
    description: '',
    budget: '',
    contact: '',
    submiting: false,
  },

  onLoad() {
    // 从 URL 参数获取预填数据
    const pages = getCurrentPages();
    const prevPage = pages[pages.length - 2];
    if (prevPage && prevPage.data.targetTier) {
      this.setData({ targetTier: prevPage.data.targetTier });
    }
  },

  // 选择咨询类型
  onConsultTypeSelect(e) {
    const { type } = e.currentTarget.dataset;
    this.setData({ consultType: type });
  },

  // 选择目标层次
  onTierSelect(e) {
    const { tier } = e.currentTarget.dataset;
    this.setData({ targetTier: tier });
  },

  // 输入标题
  onTitleInput(e) {
    this.setData({ title: e.detail.value });
  },

  // 输入详细描述
  onDescInput(e) {
    this.setData({ description: e.detail.value });
  },

  // 输入预算
  onBudgetInput(e) {
    this.setData({ budget: e.detail.value });
  },

  // 输入联系方式
  onContactInput(e) {
    this.setData({ contact: e.detail.value });
  },

  // 提交需求
  async onSubmit() {
    const { consultType, targetTier, title, description, budget, contact } = this.data;

    if (!consultType) {
      wx.showToast({ title: '请选择咨询类型', icon: 'none' });
      return;
    }
    if (!title.trim()) {
      wx.showToast({ title: '请填写需求标题', icon: 'none' });
      return;
    }
    if (!description.trim()) {
      wx.showToast({ title: '请详细描述您的需求', icon: 'none' });
      return;
    }

    this.setData({ submiting: true });

    try {
      const res = await post('/demand-requests', {
        dao_fa_type: 'zong_men',
        request_type: consultType,
        target_tier: targetTier,
        title: title.trim(),
        description: description.trim(),
        budget: parseInt(budget) || 0,
        contact: contact.trim(),
      });

      if (res && (res.success || res.id || res.code === 0)) {
        wx.showToast({ title: '发布成功！', icon: 'success' });
        setTimeout(() => {
          wx.navigateBack();
        }, 1500);
      } else {
        wx.showToast({ title: res?.msg || '发布失败', icon: 'none' });
      }
    } catch (e) {
      console.error('发布需求失败', e);
      wx.showToast({ title: '网络错误，请重试', icon: 'none' });
    } finally {
      this.setData({ submiting: false });
    }
  },
});
