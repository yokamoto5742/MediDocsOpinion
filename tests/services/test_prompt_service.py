from app.services import prompt_service


def test_get_all_prompts_empty(test_db):
    """全プロンプト取得 - 空の場合"""
    prompts = prompt_service.get_all_prompts(test_db)
    assert prompts == []


def test_get_all_prompts(test_db, sample_prompts):
    """全プロンプト取得 - データありの場合"""
    prompts = prompt_service.get_all_prompts(test_db)
    assert len(prompts) == 2
    assert prompts[0].department == "default"
    assert prompts[1].department == "眼科"


def test_get_prompt_success(test_db, sample_prompts):
    """特定プロンプト取得 - 成功"""
    prompt = prompt_service.get_prompt(
        test_db,
        department="眼科",
        document_type="他院への紹介",
        doctor="橋本義弘",
    )
    assert prompt is not None
    assert prompt.department == "眼科"
    assert prompt.content == "眼科用プロンプト"


def test_get_prompt_not_found(test_db):
    """特定プロンプト取得 - 存在しない場合"""
    prompt = prompt_service.get_prompt(
        test_db,
        department="存在しない診療科",
        document_type="存在しない文書タイプ",
        doctor="存在しない医師",
    )
    assert prompt is None


def test_create_or_update_prompt_create(test_db):
    """プロンプト作成/更新 - 新規作成"""
    prompt = prompt_service.create_or_update_prompt(
        test_db,
        department="内科",
        document_type="他院への紹介",
        doctor="田中医師",
        content="新規プロンプト",
        selected_model="Claude",
    )
    test_db.commit()
    test_db.refresh(prompt)
    assert prompt.id is not None
    assert prompt.department == "内科"
    assert prompt.content == "新規プロンプト"


def test_create_or_update_prompt_update(test_db, sample_prompts):
    """プロンプト作成/更新 - 更新"""
    original_id = sample_prompts[1].id
    prompt = prompt_service.create_or_update_prompt(
        test_db,
        department="眼科",
        document_type="他院への紹介",
        doctor="橋本義弘",
        content="更新されたプロンプト",
        selected_model="Gemini_Pro",
    )
    assert prompt.id == original_id
    assert prompt.content == "更新されたプロンプト"
    assert prompt.selected_model == "Gemini_Pro"


def test_delete_prompt_success(test_db, sample_prompts):
    """プロンプト削除 - 成功"""
    prompt_id = sample_prompts[1].id
    result = prompt_service.delete_prompt(test_db, prompt_id)
    test_db.commit()
    assert result is True

    prompts = prompt_service.get_all_prompts(test_db)
    assert len(prompts) == 1


def test_delete_prompt_not_found(test_db):
    """プロンプト削除 - 存在しないID"""
    result = prompt_service.delete_prompt(test_db, 9999)
    assert result is False


def test_get_prompt_hierarchical_fallback_doctor_specific(test_db, sample_prompts):
    """階層的フォールバック - 医師固有プロンプトが存在する場合"""
    prompt = prompt_service.get_prompt(
        test_db,
        department="眼科",
        document_type="他院への紹介",
        doctor="橋本義弘",
    )
    assert prompt is not None
    assert prompt.department == "眼科"
    assert prompt.doctor == "橋本義弘"
    assert prompt.content == "眼科用プロンプト"


def test_get_prompt_hierarchical_fallback_department_default(test_db):
    """階層的フォールバック - 診療科デフォルトプロンプトにフォールバック"""
    from app.models.prompt import Prompt

    dept_default = Prompt(
        department="内科",
        doctor="default",
        document_type="他院への紹介",
        content="内科デフォルトプロンプト",
    )
    test_db.add(dept_default)
    test_db.commit()

    prompt = prompt_service.get_prompt(
        test_db,
        department="内科",
        document_type="他院への紹介",
        doctor="山田太郎",
    )
    assert prompt is not None
    assert prompt.department == "内科"
    assert prompt.doctor == "default"
    assert prompt.content == "内科デフォルトプロンプト"


def test_get_prompt_hierarchical_fallback_global_default(test_db, sample_prompts):
    """階層的フォールバック - グローバルデフォルトにフォールバック"""
    prompt = prompt_service.get_prompt(
        test_db,
        department="内科",
        document_type="他院への紹介",
        doctor="山田太郎",
    )
    assert prompt is not None
    assert prompt.department == "default"
    assert prompt.doctor == "default"
    assert prompt.content == "デフォルトプロンプト"


def test_get_prompt_hierarchical_fallback_none(test_db):
    """階層的フォールバック - 全て存在しない場合はNone"""
    prompt = prompt_service.get_prompt(
        test_db,
        department="存在しない診療科",
        document_type="存在しない文書タイプ",
        doctor="存在しない医師",
    )
    assert prompt is None
