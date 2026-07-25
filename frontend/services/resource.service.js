/**
 * 道藏天阁资源服务层
 * @description 资源广场、灵石解锁、发布 UGC、高校百科
 */
const { request } = require('../utils/request');

/**
 * 资源列表（道藏天阁广场）
 * @param {object} params
 * @param {string} params.resource_type - question_set|experience_post|school_guide|course_note|tool
 * @param {string} params.subject - 学科
 * @param {string} params.school_level - 学段
 * @param {string} params.access_mode - free|points|paid
 * @param {string} params.keyword - 关键词搜索
 * @param {string} params.sort - hot|new|free
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页条数
 */
const listResources = (params = {}) => {
  return request({
    url: '/resources',
    data: { page: 1, page_size: 20, ...params },
  });
};

/**
 * 资源详情
 * @param {string} resourceId 资源 ID
 */
const getResourceDetail = (resourceId) => {
  return request({ url: `/resources/${resourceId}` });
};

/**
 * 发布资源（大虾）
 * @param {object} payload
 */
const publishResource = (payload) => {
  return request({
    url: '/resources',
    method: 'POST',
    data: payload,
  });
};

/**
 * 灵石解锁 / 付费解锁
 * @param {string} resourceId 资源 ID
 * @param {string} unlockMethod points | paid
 */
const unlockResource = (resourceId, unlockMethod = 'points') => {
  return request({
    url: `/resources/${resourceId}/unlock?unlock_method=${unlockMethod}`,
    method: 'POST',
  });
};

/**
 * 资源点赞
 * @param {string} resourceId 资源 ID
 */
const likeResource = (resourceId) => {
  return request({
    url: `/resources/${resourceId}/like`,
    method: 'POST',
  });
};

/**
 * 我的发布（大虾视角）
 */
const myResources = (params = {}) => {
  return request({
    url: '/resources/mine',
    data: { page: 1, page_size: 20, ...params },
  });
};

/**
 * 高校百科列表（宗门图志）
 * @param {string} keyword 关键词
 */
const listSchoolGuides = (keyword = '') => {
  return request({
    url: '/resources/school-guides',
    data: { keyword },
  });
};

/**
 * 收藏资源
 * @param {string} resourceId 资源 ID
 * @param {string} action add | remove
 */
const toggleFavorite = (resourceId, action = 'add') => {
  return request({
    url: `/resources/${resourceId}/favorite?action=${action}`,
    method: 'POST',
  });
};

/**
 * 检查收藏状态
 * @param {string} resourceId 资源 ID
 */
const checkFavoriteStatus = (resourceId) => {
  return request({
    url: `/resources/${resourceId}/favorite/status`,
  });
};

/**
 * 我的收藏列表
 */
const myFavorites = (params = {}) => {
  return request({
    url: '/resources/favorites',
    data: { page: 1, page_size: 20, ...params },
  });
};

/**
 * 资源评论列表
 * @param {string} resourceId 资源 ID
 */
const listComments = (resourceId, params = {}) => {
  return request({
    url: `/resources/${resourceId}/comments`,
    data: { page: 1, page_size: 20, ...params },
  });
};

/**
 * 添加评论
 * @param {string} resourceId 资源 ID
 * @param {string} content 评论内容
 * @param {string} parentId 回复的评论ID（可选）
 */
const addComment = (resourceId, content, parentId = null) => {
  return request({
    url: `/resources/${resourceId}/comments`,
    method: 'POST',
    data: { content, parent_id: parentId },
  });
};

/**
 * 高校百科 AI 问答
 * @param {string} question 问题
 * @param {string} schoolName 学校名称（可选）
 */
const askSchoolWiki = (question, schoolName = '') => {
  return request({
    url: '/school-wiki/ask',
    method: 'POST',
    data: { question, school_name: schoolName },
  });
};

/**
 * 获取高校列表
 */
const getSchoolList = () => {
  return request({
    url: '/school-wiki/schools',
  });
};

/**
 * 搜索高校
 * @param {string} keyword 关键词
 */
const searchSchool = (keyword) => {
  return request({
    url: '/school-wiki/search',
    data: { keyword },
  });
};

/**
 * 获取高校详情
 * @param {string} schoolName 学校名称
 */
const getSchoolDetail = (schoolName) => {
  return request({
    url: `/school-wiki/detail/${encodeURIComponent(schoolName)}`,
  });
};

/**
 * 获取问答历史
 */
const getQAHistory = (params = {}) => {
  return request({
    url: '/school-wiki/history',
    data: { page: 1, page_size: 20, ...params },
  });
};

// ── 资源类型中文映射 ──────────────────────────────────────
const RESOURCE_TYPE_MAP = {
  question_set: '题库',
  experience_post: '经验帖',
  school_guide: '宗门图志',
  course_note: '课程笔记',
  tool: '工具攻略',
};

module.exports = {
  listResources,
  getResourceDetail,
  publishResource,
  unlockResource,
  likeResource,
  myResources,
  listSchoolGuides,
  askSchoolWiki,
  getSchoolList,
  searchSchool,
  getSchoolDetail,
  getQAHistory,
  toggleFavorite,
  checkFavoriteStatus,
  myFavorites,
  listComments,
  addComment,
  RESOURCE_TYPE_MAP,
};
