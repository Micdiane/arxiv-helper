/**
 * ArXiv Helper 主JavaScript文件
 * 
 * 包含全局共享的函数和工具
 */

// 等待DOM加载完成
document.addEventListener('DOMContentLoaded', function() {
    // 添加导航高亮
    highlightCurrentNavItem();
});

/**
 * 根据当前页面URL高亮导航菜单项
 */
function highlightCurrentNavItem() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('nav a');
    
    navLinks.forEach(link => {
        // 移除所有高亮
        link.classList.remove('active');
        
        // 获取链接路径
        const linkPath = link.getAttribute('href');
        
        // 主页特殊处理
        if (linkPath === '/' && (currentPath === '/' || currentPath === '')) {
            link.classList.add('active');
        }
        // 其他页面
        else if (linkPath !== '/' && currentPath.startsWith(linkPath)) {
            link.classList.add('active');
        }
    });
}

/**
 * 格式化日期
 * 
 * @param {string} dateString - ISO格式的日期字符串
 * @returns {string} 格式化后的日期字符串
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN');
}

/**
 * 截断文本
 * 
 * @param {string} text - 要截断的文本
 * @param {number} maxLength - 最大长度
 * @returns {string} 截断后的文本
 */
function truncateText(text, maxLength) {
    if (!text) return '';
    
    if (text.length <= maxLength) {
        return text;
    }
    
    return text.substring(0, maxLength) + '...';
}

/**
 * 显示通知
 * 
 * @param {string} message - 通知消息
 * @param {string} type - 通知类型 (success, error, info)
 * @param {number} duration - 显示时长（毫秒）
 */
function showNotification(message, type = 'info', duration = 3000) {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // 添加到页面
    document.body.appendChild(notification);
    
    // 显示通知
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // 设置自动消失
    setTimeout(() => {
        notification.classList.remove('show');
        
        // 移除元素
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, duration);
}

/**
 * 切换论文收藏状态
 * 
 * @param {string} arxivId - 论文的ArXiv ID
 * @param {HTMLElement} button - 收藏按钮元素
 * @param {Function} callback - 可选的回调函数
 */
function toggleFavorite(arxivId, button, callback = null) {
    fetch(`/api/library/${arxivId}/toggle`, {
        method: 'POST',
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('请求失败');
            }
            return response.json();
        })
        .then(data => {
            if (data.is_favorite) {
                button.classList.add('active');
                showNotification('已添加到收藏夹', 'success');
            } else {
                button.classList.remove('active');
                showNotification('已从收藏夹移除', 'info');
            }
            
            // 执行回调
            if (callback) {
                callback(data);
            }
        })
        .catch(error => {
            console.error('切换收藏状态失败:', error);
            showNotification('操作失败，请重试', 'error');
        });
} 