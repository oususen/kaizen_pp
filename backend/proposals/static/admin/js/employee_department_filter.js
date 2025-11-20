(function($) {
    'use strict';

    $(document).ready(function() {
        // 全ての部門データを保存
        var allGroups = [];
        var allTeams = [];

        // 初期データを保存
        $('#id_group_dept option').each(function() {
            if ($(this).val()) {
                allGroups.push({
                    value: $(this).val(),
                    text: $(this).text(),
                    parent: $(this).data('parent')
                });
            }
        });

        $('#id_team_dept option').each(function() {
            if ($(this).val()) {
                allTeams.push({
                    value: $(this).val(),
                    text: $(this).text(),
                    parent: $(this).data('parent')
                });
            }
        });

        // 部門データを取得してdata属性に追加
        function loadDepartmentData() {
            $.ajax({
                url: '/api/departments/?page_size=200',
                method: 'GET',
                success: function(data) {
                    var departments = Array.isArray(data) ? data : (data.results || []);

                    // 部門IDと親IDのマッピングを作成
                    var deptMap = {};
                    departments.forEach(function(dept) {
                        deptMap[dept.id] = dept;
                    });

                    // グループの親情報を更新
                    allGroups = [];
                    $('#id_group_dept option').each(function() {
                        var val = $(this).val();
                        if (val) {
                            var dept = deptMap[val];
                            allGroups.push({
                                value: val,
                                text: $(this).text(),
                                parent: dept ? dept.parent : null
                            });
                        }
                    });

                    // チームの親情報を更新
                    allTeams = [];
                    $('#id_team_dept option').each(function() {
                        var val = $(this).val();
                        if (val) {
                            var dept = deptMap[val];
                            allTeams.push({
                                value: val,
                                text: $(this).text(),
                                parent: dept ? dept.parent : null
                            });
                        }
                    });

                    // 初期フィルタを適用
                    filterGroupsByDivision();
                    filterTeamsByGroup();
                }
            });
        }

        // 事業部に基づいて係をフィルタ
        function filterGroupsByDivision() {
            var divisionId = $('#id_division_dept').val();
            var currentValue = $('#id_group_dept').val();

            $('#id_group_dept option').not(':first').remove();

            if (divisionId) {
                allGroups.forEach(function(group) {
                    if (group.parent == divisionId) {
                        $('#id_group_dept').append(
                            $('<option></option>').val(group.value).text(group.text)
                        );
                    }
                });

                // 現在の値が有効なら再選択
                if (currentValue && $('#id_group_dept option[value="' + currentValue + '"]').length > 0) {
                    $('#id_group_dept').val(currentValue);
                } else {
                    $('#id_group_dept').val('');
                }
            } else {
                // 部門が未選択なら全て表示
                allGroups.forEach(function(group) {
                    $('#id_group_dept').append(
                        $('<option></option>').val(group.value).text(group.text)
                    );
                });
                $('#id_group_dept').val(currentValue);
            }
        }

        // 係に基づいて班をフィルタ
        function filterTeamsByGroup() {
            var groupId = $('#id_group_dept').val();
            var currentValue = $('#id_team_dept').val();

            $('#id_team_dept option').not(':first').remove();

            if (groupId) {
                allTeams.forEach(function(team) {
                    if (team.parent == groupId) {
                        $('#id_team_dept').append(
                            $('<option></option>').val(team.value).text(team.text)
                        );
                    }
                });

                // 現在の値が有効なら再選択
                if (currentValue && $('#id_team_dept option[value="' + currentValue + '"]').length > 0) {
                    $('#id_team_dept').val(currentValue);
                } else {
                    $('#id_team_dept').val('');
                }
            } else {
                // 係が未選択なら全て表示
                allTeams.forEach(function(team) {
                    $('#id_team_dept').append(
                        $('<option></option>').val(team.value).text(team.text)
                    );
                });
                $('#id_team_dept').val(currentValue);
            }
        }

        // イベントリスナーを設定
        $('#id_division_dept').on('change', function() {
            filterGroupsByDivision();
            filterTeamsByGroup(); // 係が変わるので班もリセット
        });

        $('#id_group_dept').on('change', function() {
            filterTeamsByGroup();
        });

        // データをロード
        loadDepartmentData();
    });
})(django.jQuery);
