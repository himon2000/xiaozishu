/**
 * 传功授法 - 发布服务页面
 * 路径：pages/publish-service/publish-service
 */
const { post } = require('../../utils/request');
const { uploadImage } = require('../../utils/upload');
const { ensurePrivacyAuthorized } = require('../../utils/privacy');

Page({
  data: {
    submitting: false,
    // 服务类型
    serviceTypes: [
      { id: 'tutoring', name: '📚 学科辅导', desc: '数学/物理/编程等课程辅导', icon: '📚' },
      { id: 'competition', name: '🏆 竞赛陪练', desc: '建模/ACM/挑战杯等竞赛指导', icon: '🏆' },
      { id: 'exam_prep', name: '✏️ 考前冲刺', desc: '考研/四六级/期末冲刺', icon: '✏️' },
      { id: 'thesis', name: '📄 论文指导', desc: '论文写作/发表指导', icon: '📄' },
    ],
    formData: {
      title: '',
      service_type: 'tutoring',  // 默认学科辅导
      subjects: [],  // 选择的科目
      description: '',
      cover_image: '',
      tags: '',
      pricing_mode: 'free',
      price: '',
      unit: '次',
      min_sessions: 1,
      delivery_methods: [],
      teaching_style: '',
      achievements: [],  // 战绩
      cases: [],  // 案例
      expertise: [],  // 擅长领域
    },
    // 科目分类
    subjectsByCategory: {
      '理工': [
        { id: 'math', name: '高等数学', icon: '📐' },
        { id: 'linear_algebra', name: '线性代数', icon: '📊' },
        { id: 'probability', name: '概率论/数理统计', icon: '🎲' },
        { id: 'physics', name: '大学物理', icon: '⚡' },
        { id: 'chemistry', name: '大学化学', icon: '🧪' },
        { id: 'programming', name: '编程/Python/C++', icon: '💻' },
        { id: 'data_structure', name: '数据结构与算法', icon: '🔢' },
        { id: 'circuit', name: '电路/电子技术', icon: '🔌' },
      ],
      '文科': [
        { id: 'english', name: '英语/四六级', icon: '🇬🇧' },
        { id: 'chinese', name: '大学语文/写作', icon: '📝' },
        { id: 'economics', name: '经济学/金融学', icon: '💹' },
        { id: 'management', name: '管理学/市场营销', icon: '📋' },
        { id: 'law', name: '法学/法律', icon: '⚖️' },
      ],
      '竞赛': [
        { id: 'math建模', name: '数学建模竞赛', icon: '🏆' },
        { id: 'acm', name: 'ACM/ICPC编程竞赛', icon: '🏆' },
        { id: 'challenge_cup', name: '挑战杯/创青春', icon: '🏆' },
        { id: 'innovation', name: '大创/互联网+', icon: '🏆' },
        { id: 'math_competition', name: '数学竞赛', icon: '🏆' },
        { id: 'physics_competition', name: '物理竞赛', icon: '🏆' },
      ],
      '考试': [
        { id: 'postgraduate', name: '考研全套辅导', icon: '🎓' },
        { id: 'toefl_ielts', name: '托福/雅思', icon: '🌍' },
        { id: 'gmat_gre', name: 'GMAT/GRE', icon: '📚' },
        { id: 'cfa_frm', name: 'CFA/FRM金融证书', icon: '💰' },
        { id: 'cpa', name: 'CPA/ACCA会计证书', icon: '📊' },
      ],
    },
    // 竞赛等级
    competitionLevels: [
      { id: 'school', name: '校级', color: '#95a5a6' },
      { id: 'city', name: '市级', color: '#3498db' },
      { id: 'provincial', name: '省级', color: '#9b59b6' },
      { id: 'national', name: '国家级', color: '#e74c3c' },
      { id: 'world', name: '国际级', color: '#f39c12' },
    ],
    // 交付方式
    deliveryMethods: [
      { id: 'online', name: '💻 在线辅导', icon: '💻' },
      { id: 'offline', name: '🏠 线下面授', icon: '🏠' },
      { id: 'video', name: '🎬 视频课程', icon: '🎬' },
      { id: 'material', name: '📁 资料提供', icon: '📁' },
    ],
    // 定价方式
    pricingModes: [
      { id: 'free', name: '免费（首个公众版本）', unit: '' },
    ],
    // 教学风格选项
    teachingStyles: [
      '幽默风趣',
      '严谨认真',
      '耐心细致',
      '高效实战',
      '循循善诱',
    ],
    // UI状态
    showSubjectPicker: false,
    showAchievementModal: false,
    showCaseModal: false,
    newAchievement: { type: '', level: '', name: '', year: '' },
    newCase: { title: '', description: '', result: '' },
  },

  onLoad(options) {
    // 如果有预填的道法类型
    if (options.dao_fa_type) {
      this.setData({ daoFaType: options.dao_fa_type });
    }
  },

  // 服务类型选择
  onServiceTypeSelect(e) {
    const { id } = e.currentTarget.dataset;
    this.setData({
      'formData.service_type': id,
      'formData.subjects': [],  // 切换类型时清空科目
    });
  },

  // 科目分类选择（切换分类）
  onSubjectCategoryChange(e) {
    const categories = Object.keys(this.data.subjectsByCategory);
    const currentIdx = categories.indexOf(this.data.currentSubjectCategory || '理工');
    const nextIdx = (currentIdx + 1) % categories.length;
    this.setData({ currentSubjectCategory: categories[nextIdx] });
  },

  // 切换科目弹窗
  onToggleSubjectPicker() {
    const categories = Object.keys(this.data.subjectsByCategory);
    this.setData({
      showSubjectPicker: true,
      currentSubjectCategory: categories[0],
    });
  },

  // 选择/取消科目
  onSubjectToggle(e) {
    const { id } = e.currentTarget.dataset;
    const subjects = this.data.formData.subjects;
    const idx = subjects.indexOf(id);
    if (idx >= 0) {
      subjects.splice(idx, 1);
    } else {
      subjects.push(id);
    }
    this.setData({ 'formData.subjects': subjects });
  },

  // 确认科目选择
  onConfirmSubjects() {
    this.setData({ showSubjectPicker: false });
  },

  // 标题输入
  onTitleInput(e) {
    this.setData({ 'formData.title': e.detail.value });
  },

  // 描述输入
  onDescriptionInput(e) {
    this.setData({ 'formData.description': e.detail.value });
  },

  // 标签输入
  onTagsInput(e) {
    this.setData({ 'formData.tags': e.detail.value });
  },

  // 选择封面
  async onChooseCover() {
    try {
      await ensurePrivacyAuthorized();
    } catch (error) {
      return;
    }
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sizeType: ['compressed'],
      success: (res) => {
        const filePath = res.tempFiles[0].tempFilePath;
        this.setData({ 'formData.cover_image': filePath });
      },
    });
  },

  // 删除封面
  onRemoveCover() {
    this.setData({ 'formData.cover_image': '' });
  },

  // 定价方式选择
  onPricingModeSelect(e) {
    const { id, unit } = e.currentTarget.dataset;
    this.setData({
      'formData.pricing_mode': id,
      'formData.unit': unit,
    });
  },

  // 价格输入
  onPriceInput(e) {
    const val = parseInt(e.detail.value, 10);
    if (val > 10000) {
      this.setData({ 'formData.price': '10000' });
    } else {
      this.setData({ 'formData.price': e.detail.value });
    }
  },

  // 最小课次选择
  onMinSessionsChange(e) {
    this.setData({ 'formData.min_sessions': parseInt(e.detail.value, 10) });
  },

  // 交付方式选择
  onDeliveryMethodToggle(e) {
    const { id } = e.currentTarget.dataset;
    const methods = this.data.formData.delivery_methods;
    const idx = methods.indexOf(id);
    if (idx >= 0) {
      methods.splice(idx, 1);
    } else {
      methods.push(id);
    }
    this.setData({ 'formData.delivery_methods': methods });
  },

  // 教学风格选择
  onTeachingStyleSelect(e) {
    const { style } = e.currentTarget.dataset;
    this.setData({ 'formData.teaching_style': style });
  },

  // ── 战绩管理 ──────────────────────────────────

  // 添加战绩弹窗
  onAddAchievement() {
    this.setData({
      showAchievementModal: true,
      newAchievement: { type: '', level: '', name: '', year: '' },
    });
  },

  // 战绩类型选择
  onAchievementTypeSelect(e) {
    const { id } = e.currentTarget.dataset;
    this.setData({ 'newAchievement.type': id });
  },

  // 战绩等级选择
  onAchievementLevelSelect(e) {
    const { id } = e.currentTarget.dataset;
    this.setData({ 'newAchievement.level': id });
  },

  // 战绩名称输入
  onAchievementNameInput(e) {
    this.setData({ 'newAchievement.name': e.detail.value });
  },

  // 战绩年份输入
  onAchievementYearInput(e) {
    this.setData({ 'newAchievement.year': e.detail.value });
  },

  // 确认添加战绩
  onConfirmAchievement() {
    const { type, level, name, year } = this.data.newAchievement;
    if (!type || !name) {
      wx.showToast({ title: '请填写完整战绩信息', icon: 'none' });
      return;
    }
    const achievements = [...this.data.formData.achievements, { type, level, name, year }];
    this.setData({
      'formData.achievements': achievements,
      showAchievementModal: false,
    });
  },

  // 删除战绩
  onDeleteAchievement(e) {
    const { index } = e.currentTarget.dataset;
    const achievements = this.data.formData.achievements;
    achievements.splice(index, 1);
    this.setData({ 'formData.achievements': achievements });
  },

  // ── 案例管理 ──────────────────────────────────

  // 添加案例弹窗
  onAddCase() {
    this.setData({
      showCaseModal: true,
      newCase: { title: '', description: '', result: '' },
    });
  },

  // 案例标题输入
  onCaseTitleInput(e) {
    this.setData({ 'newCase.title': e.detail.value });
  },

  // 案例描述输入
  onCaseDescInput(e) {
    this.setData({ 'newCase.description': e.detail.value });
  },

  // 案例结果输入
  onCaseResultInput(e) {
    this.setData({ 'newCase.result': e.detail.value });
  },

  // 确认添加案例
  onConfirmCase() {
    const { title, description, result } = this.data.newCase;
    if (!title) {
      wx.showToast({ title: '请填写案例标题', icon: 'none' });
      return;
    }
    const cases = [...this.data.formData.cases, { title, description, result }];
    this.setData({
      'formData.cases': cases,
      showCaseModal: false,
    });
  },

  // 删除案例
  onDeleteCase(e) {
    const { index } = e.currentTarget.dataset;
    const cases = this.data.formData.cases;
    cases.splice(index, 1);
    this.setData({ 'formData.cases': cases });
  },

  // ── 提交 ──────────────────────────────────

  async onSubmit() {
    const { formData } = this.data;

    // 验证必填项
    if (!formData.title || formData.title.trim().length < 5) {
      wx.showToast({ title: '请填写服务标题（至少5个字）', icon: 'none' });
      return;
    }
    if (!formData.description || formData.description.trim().length < 20) {
      wx.showToast({ title: '请填写详细说明（至少20个字）', icon: 'none' });
      return;
    }
    if (formData.subjects.length === 0) {
      wx.showToast({ title: '请选择至少一个科目', icon: 'none' });
      return;
    }
    if (formData.pricing_mode !== 'free') {
      const price = parseInt(formData.price, 10);
      if (!price || price < 1) {
        wx.showToast({ title: '请设置服务价格', icon: 'none' });
        return;
      }
    }
    if (formData.delivery_methods.length === 0) {
      wx.showToast({ title: '请选择交付方式', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });

    try {
      const coverImage = formData.cover_image
        ? await uploadImage(formData.cover_image, 'service-covers')
        : '';
      const payload = {
        dao_fa_type: 'chuan_gong',  // 传功授法
        title: formData.title.trim(),
        description: formData.description.trim(),
        service_type: formData.service_type,
        subjects: formData.subjects,
        tags: formData.tags ? formData.tags.split(/[,，]/).map(t => t.trim()).filter(t => t) : [],
        cover_image: coverImage,
        pricing_mode: formData.pricing_mode,
        price: parseInt(formData.price || '0', 10) * 100,  // 转换为分
        unit: formData.unit,
        min_sessions: formData.min_sessions,
        delivery_methods: formData.delivery_methods,
        teaching_style: formData.teaching_style,
        achievements: formData.achievements,
        cases: formData.cases,
      };

      const res = await post('/services', payload);
      wx.showToast({ title: '发布成功！', icon: 'success' });
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
    } catch (e) {
      wx.showToast({ title: e.message || '发布失败', icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
