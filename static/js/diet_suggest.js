document.addEventListener('DOMContentLoaded', function() {
    
    // 抓取我們剛剛在 day.html 設定好 ID 的所有 DOM 元素
    const foodInput = document.getElementById('food_name_input');
    const suggestionsBox = document.getElementById('suggestions_box');
    
    const kcalInput = document.getElementById('kcal_input');
    const proteinInput = document.getElementById('protein_input');
    const fatInput = document.getElementById('fat_input');
    const carbInput = document.getElementById('carb_input');

    // 防呆：如果頁面上找不到這些元素，就提早結束，避免錯誤
    if (!foodInput || !suggestionsBox || !kcalInput || !proteinInput || !fatInput || !carbInput) {
        // console.log("Diet suggest inputs not found on this page.");
        return;
    }

    // 當使用者在 "食品名稱" 欄位打字時...
    foodInput.addEventListener('input', async function() {
        const query = foodInput.value;
        
        // 清空舊的建議
        suggestionsBox.innerHTML = '';
        
        if (query.length < 1) {
            suggestionsBox.style.display = 'none';
            return; // 至少要輸入一個字
        }

        // 去呼叫我們的後端 API
        try {
            const response = await fetch(`/api/diet/suggest?q=${encodeURIComponent(query)}`);
            if (!response.ok) return;
            
            const suggestions = await response.json();

            if (suggestions.length > 0) {
                // 如果 API 有回傳建議...
                suggestionsBox.style.display = 'block'; // 顯示建議框
                
                suggestions.forEach(item => {
                    // 建立每一個建議選項
                    const suggestionItem = document.createElement('div');
                    suggestionItem.className = 'suggestion-item'; // 方便我們寫 CSS
                    
                    // 顯示名稱和熱量
                    suggestionItem.textContent = `${item.name} (${item.kcal || 0} kcal)`;
                    
                    // 當 "點擊" 某個建議時...
                    suggestionItem.addEventListener('click', function() {
                        // 1. 自動填入所有欄位
                        foodInput.value = item.name;
                        kcalInput.value = item.kcal || 0;
                        proteinInput.value = item.protein || 0;
                        fatInput.value = item.fat || 0;
                        carbInput.value = item.carb || 0;
                        
                        // 2. 隱藏建議列表
                        suggestionsBox.innerHTML = '';
                        suggestionsBox.style.display = 'none';
                    });
                    
                    suggestionsBox.appendChild(suggestionItem);
                });
            } else {
                suggestionsBox.style.display = 'none'; // 沒建議就隱藏
            }
        } catch (error) {
            console.error('Error fetching diet suggestions:', error);
            suggestionsBox.style.display = 'none';
        }
    });

    // 當使用者點擊頁面其他地方時，隱藏建議列表
    document.addEventListener('click', function(e) {
        // 只有當點擊的目標不是 foodInput 本身時才隱藏
        if (e.target !== foodInput) {
            suggestionsBox.style.display = 'none';
        }
    });
});