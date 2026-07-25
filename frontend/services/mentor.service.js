/**
 * 道友传承服务层
 * @description 寻访导师、申请传承、传承关系管理、传承树
 * 支持企业导师（长老）+ 学术导师（大虾）双轨体系
 */
const { request } = require('../utils/request');

/**
 * 寻访导师列表（支持按导师类型筛选）
 * @param {Object} params - { mentor_type: 'enterprise'|'academic', min_level, subject, page, page_size }
 */
const listMentors = (params = {}) => {
  return request({
    url: '/mentorships/mentors',
    data: params,
  });
};

/**
 * 我的道友传承关系（被传承者视角 + 导师视角）
 */
const getMyMentorships = () => {
  return request({ url: '/mentorships/mine' });
};

/**
 * 申请道友传承
 * @param {string} mentorOpenid 导师 openid
 * @param {string} message 申请理由
 * @param {string} mentorType 'enterprise'=企业导师，'academic'=学术导师
 * @param {string} mentorDirection 'employment'=就业方向，'academic'=学术方向
 */
const applyMentorship = (mentorOpenid, message = '', mentorType = 'academic', mentorDirection = 'academic') => {
  return request({
    url: '/mentorships/apply',
    method: 'POST',
    data: {
      mentor_openid: mentorOpenid,
      message,
      mentor_type: mentorType,
      mentor_direction: mentorDirection,
    },
  });
};

/**
 * 传承树数据
 * @param {string} mentorshipId 道友传承关系 ID
 */
const getLineageTree = (mentorshipId) => {
  return request({ url: `/mentorships/${mentorshipId}/lineage` });
};

/**
 * 记录被传承者里程碑（导师操作）
 * @param {string} mentorshipId 道友传承关系 ID
 * @param {string} event 事件类型
 * @param {string} remark 备注
 */
const recordMilestone = (mentorshipId, event, remark = '') => {
  return request({
    url: `/mentorships/${mentorshipId}/milestone`,
    method: 'POST',
    data: { event, remark },
  });
};

/**
 * 解除道友传承关系
 * @param {string} mentorshipId 道友传承关系 ID
 */
const dissolveMentorship = (mentorshipId) => {
  return request({
    url: `/mentorships/${mentorshipId}/dissolve`,
    method: 'POST',
  });
};

/**
 * 导师详情（含服务列表 + 评价 + 传承树）
 * @param {string} openid 导师 openid
 */
const getMentorProfile = (openid) => {
  return request({ url: `/services/provider/${openid}` });
};

module.exports = {
  listMentors,
  getMyMentorships,
  applyMentorship,
  getLineageTree,
  recordMilestone,
  dissolveMentorship,
  getMentorProfile,
};
