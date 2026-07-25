/**
 * 添加人生阶段页面
 */
const { post } = require('../../../utils/request');

Page({
  data: {
    form: {
      stage_type: 'college',  // 默认大学阶段
      stage_name: '',
      role: 'seeker',
      // 高中
      high_school_name: '',
      high_school_city: '',
      grade: '',
      // 大学
      school: '',
      school_level: '',
      major: '',
      // 职场
      company: '',
      position: '',
      industry: '',
      // 通用
      city: '',
    },
    gradeOptions: ['高一', '高二', '高三', '高四（复读）'],
    schoolLevelOptions: ['本科', '硕士', '博士', 'MBA', '其他'],
    submitting: false,
  },

  onLoad() {
    // 设置默认阶段名称
    this.setDefaultStageName();
  },

  // 设置默认阶段名称
  setDefaultStageName() {
    const type = this.data.form.stage_type;
    const names = {
      'high_school': '高中阶段',
      'college': '大学阶段',
      'working': '职场阶段',
    };
    this.setData({
      'form.stage_name': names[type]
    });
  },

  // 选择阶段类型
  onSelectType(e) {
    const type = e.currentTarget.dataset.type;
    this.setData({
      'form.stage_type': type
    });
    this.setDefaultStageName();
  },

  // 选择角色
  onSelectRole(e) {
    const role = e.currentTarget.dataset.role;
    this.setData({
      'form.role': role
    });
  },

  // 输入处理
  onInput(e) {
    const field = e.currentTarget.dataset.field;
    this.setData({
      [`form.${field}`]: e.detail.value
    });
  },

  // 年级选择
  onGradeChange(e) {
    const index = e.detail.value;
    this.setData({
      'form.grade': this.data.gradeOptions[index]
    });
  },

  // 学历选择
  onSchoolLevelChange(e) {
    const index = e.detail.value;
    this.setData({
      'form.school_level': this.data.schoolLevelOptions[index]
    });
  },

  // 提交
  async onSubmit() {
    const form = this.data.form;

    // 验证
    if (!form.stage_type) {
      wx.showToast({ title: '请选择阶段类型', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });

    try {
      await post('/stages', form);
      wx.showToast({ title: '创建成功', icon: 'success' });
      // 通知上一页刷新数据
      const pages = getCurrentPages();
      if (pages.length > 1) {
        const prevPage = pages[pages.length - 2];
        if (prevPage && typeof prevPage.loadData === 'function') {
          prevPage.loadData();
        }
      }
      // 延迟返回
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
    } catch (e) {
      console.error('创建阶段失败', e);
      wx.showToast({ title: e.message || '创建失败', icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
