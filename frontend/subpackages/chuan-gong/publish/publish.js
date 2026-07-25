/**
 * 传功授法 - 发布需求页
 * 快速发布辅导需求
 * 路径：subpackages/chuan-gong/publish/publish
 */
const { post } = require('../../../utils/request');

Page({
  data: {
    // 表单数据
    subject: '',          // 科目
    serviceType: '',      // 服务类型
    schoolLevel: '',      // 学段
    target: '',           // 辅导目标
    budget: '',           // 预算
    description: '',      // 详细描述
    contact: '',          // 联系方式

    // 选项列表
    subjects: [
      { id: 'math', name: '高等数学' },
      { id: 'linear_algebra', name: '线性代数' },
      { id: 'probability', name: '概率论' },
      { id: 'physics', name: '大学物理' },
      { id: 'programming', name: 'C/C++/Python' },
      { id: 'data_structure', name: '数据结构' },
      { id: 'english', name: '英语' },
      { id: 'economics', name: '经济学' },
      { id: 'thesis', name: '论文' },
    ],
    serviceTypes: [
      { id: 'tutoring', name: '长期辅导' },
      { id: 'exam_prep', name: '考前冲刺' },
      { id: 'competition', name: '竞赛指导' },
    ],
    schoolLevels: [
      { id: 'undergraduate', name: '本科' },
      { id: 'master', name: '硕士' },
      { id: 'doctor', name: '博士' },
    ],
    budgetOptions: [
      { value: '50-100', label: '50-100元/次' },
      { value: '100-200', label: '100-200元/次' },
      { value: '200-500', label: '200-500元/次' },
      { value: '500+', label: '500元+/次' },
    ],

    submitting: false,
  },

  onLoad(options) {
    // 预填科目
    if (options.subject) {
      this.setData({ subject: options.subject });
    }
  },

  // ========== 表单选择 ==========
  onSubjectSelect(e) {
    const subject = e.currentTarget.dataset.subject;
    this.setData({ subject: this.data.subject === subject ? '' : subject });
  },

  onTypeSelect(e) {
    const type = e.currentTarget.dataset.type;
    this.setData({ serviceType: type });
  },

  onLevelSelect(e) {
    const level = e.currentTarget.dataset.level;
    this.setData({ schoolLevel: level });
  },

  onBudgetInput(e) {
    this.setData({ budget: e.detail.value });
  },

  onTargetInput(e) {
    this.setData({ target: e.detail.value });
  },

  onDescriptionInput(e) {
    this.setData({ description: e.detail.value });
  },

  onContactInput(e) {
    this.setData({ contact: e.detail.value });
  },

  // ========== 提交 ==========
  async onSubmit() {
    const { subject, serviceType, schoolLevel, target, description } = this.data;

    if (!subject) {
      wx.showToast({ title: '请选择科目', icon: 'none' });
      return;
    }
    if (!serviceType) {
      wx.showToast({ title: '请选择辅导类型', icon: 'none' });
      return;
    }
    if (!description) {
      wx.showToast({ title: '请填写需求描述', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });
    try {
      // TODO: 调用发布需求接口
      // 暂时模拟成功
      await new Promise(resolve => setTimeout(resolve, 1000));

      wx.showModal({
        title: '✅ 发布成功',
        content: '您的需求已发布，等待导师接单！',
        showCancel: false,
        success: () => {
          wx.navigateBack();
        }
      });
    } catch (e) {
      console.error('发布失败', e);
      wx.showToast({ title: '发布失败，请重试', icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
