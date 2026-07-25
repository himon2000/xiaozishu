/**
 * 统一 API 服务层（子包内共享）
 */
const { request, get, post, put, patch, del } = require('../../utils/request');

module.exports = {
  request,
  get,
  post,
  put,
  patch,
  del,
};
