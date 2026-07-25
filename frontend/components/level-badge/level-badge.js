/**
 * 境界徽章组件
 * <level-badge level="{{3}}" />
 */
Component({
  properties: {
    level: { type: Number, value: 1 },
    size: { type: String, value: 'md' },  // sm | md | lg
    showName: { type: Boolean, value: true },
  },

  data: {
    config: { name: '炼气期', icon: '🌫', color: '#999999' },
  },

  lifetimes: {
    attached() {
      this._updateConfig();
    },
  },

  observers: {
    level(newLevel) {
      this._updateConfig(newLevel);
    },
  },

  methods: {
    _updateConfig(level) {
      const configs = [
        { name: '炼气期', icon: '🌫', color: '#999999' },
        { name: '筑基期', icon: '🌿', color: '#00cc44' },
        { name: '金丹期', icon: '💙', color: '#4499ff' },
        { name: '元婴期', icon: '💜', color: '#cc44ff' },
        { name: '化神期', icon: '⭐', color: '#ffd700' },
      ];
      const lv = level !== undefined ? level : this.data.level;
      this.setData({ config: configs[lv - 1] || configs[0] });
    },
  },
});
