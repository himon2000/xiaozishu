/**
 * 下山历练 - 发布机会
 * 路径：subpackages/xiashan/publish/publish
 */
const { post } = require('../../../utils/request');

Page({
  data: {
    // 岗位类型
    jobTypes: [
      { id: 'intern', name: '实习岗位', icon: '💼' },
      { id: 'parttime', name: '兼职', icon: '📋' },
      { id: 'fulltime', name: '全职', icon: '🏢' },
      { id: 'referral', name: '内推', icon: '🎯' },
    ],
    // 当前选中的值
    jobType: '',
    title: '',
    company: '',
    salary: '',
    location: '',
    description: '',
    requirements: '',
    contact: '',
    submiting: false,
  },

  onLoad() {
    // 从 URL 参数获取预填数据
    const pages = getCurrentPages();
    const prevPage = pages[pages.length - 2];
    if (prevPage && prevPage.data.jobType) {
      this.setData({ jobType: prevPage.data.jobType });
    }
  },

  // 选择岗位类型
  onJobTypeSelect(e) {
    const { type } = e.currentTarget.dataset;
    this.setData({ jobType: type });
  },

  // 输入岗位名称
  onTitleInput(e) {
    this.setData({ title: e.detail.value });
  },

  // 输入公司名称
  onCompanyInput(e) {
    this.setData({ company: e.detail.value });
  },

  // 输入薪资
  onSalaryInput(e) {
    this.setData({ salary: e.detail.value });
  },

  // 输入工作地点
  onLocationInput(e) {
    this.setData({ location: e.detail.value });
  },

  // 输入岗位描述
  onDescInput(e) {
    this.setData({ description: e.detail.value });
  },

  // 输入岗位要求
  onReqInput(e) {
    this.setData({ requirements: e.detail.value });
  },

  // 输入联系方式
  onContactInput(e) {
    this.setData({ contact: e.detail.value });
  },

  // 提交
  async onSubmit() {
    const { jobType, title, company, salary, location, description, requirements, contact } = this.data;

    if (!jobType) {
      wx.showToast({ title: '请选择岗位类型', icon: 'none' });
      return;
    }
    if (!title.trim()) {
      wx.showToast({ title: '请填写岗位名称', icon: 'none' });
      return;
    }
    if (!company.trim()) {
      wx.showToast({ title: '请填写公司名称', icon: 'none' });
      return;
    }
    if (!description.trim()) {
      wx.showToast({ title: '请填写岗位描述', icon: 'none' });
      return;
    }

    this.setData({ submiting: true });

    try {
      const opportunityTypeMap = {
        intern: 'internship',
        referral: 'referral',
        parttime: 'job',
        fulltime: 'job',
      };
      const res = await post('/opportunities', {
        opportunity_type: opportunityTypeMap[jobType] || 'job',
        title: title.trim(),
        company_name: company.trim(),
        position: title.trim(),
        position_type: jobType,
        salary_range: salary.trim(),
        work_location: location.trim(),
        description: description.trim(),
        requirements: requirements.trim(),
        contact_wx: contact.trim(),
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
      console.error('发布机会失败', e);
      wx.showToast({ title: '网络错误，请重试', icon: 'none' });
    } finally {
      this.setData({ submiting: false });
    }
  },
});
