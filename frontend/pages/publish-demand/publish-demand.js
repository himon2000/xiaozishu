/**
 * 发布需求页面
 * 路径：pages/publish-demand/publish-demand
 */
const { post } = require('../../utils/request');

Page({
  data: {
    // 需求类型
    demandTypes: [
      { id: 'tutor', name: '找辅导', icon: '👨‍🏫', desc: '学科辅导/竞赛指导' },
      { id: 'team', name: '找组队', icon: '👥', desc: '课题/竞赛/活动组队' },
      { id: 'intern', name: '找实习', icon: '💼', desc: '实习/兼职机会' },
      { id: 'consult', name: '找咨询', icon: '🎯', desc: '志愿/备考咨询' },
    ],
    // 当前选中的值
    demandType: '',
    title: '',
    description: '',
    budget: '',
    contact: '',
    submiting: false,
  },

  onLoad(options) {
    // 从 URL 参数获取预填类型
    if (options.type) {
      this.setData({ demandType: options.type });
    }
  },

  // 选择需求类型
  onTypeSelect(e) {
    const { type } = e.currentTarget.dataset;
    this.setData({ demandType: type });
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
    const { demandType, title, description, budget, contact } = this.data;

    if (!demandType) {
      wx.showToast({ title: '请选择需求类型', icon: 'none' });
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
      const res = await post('/demands', {
        type: demandType,
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
