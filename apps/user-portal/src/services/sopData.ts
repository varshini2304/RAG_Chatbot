/**
 * SOP Data Model & Demonstration Datasets
 *
 * Provides benchmark datasets matching the reference specification:
 * 1. STANDARD_AUDIO_WORKFLOW: const_01.mp4 (91.47 MB, 09:05, H.264, AAC 48kHz, Japanese dialogue, 12 steps)
 * 2. SILENT_INSPECTION_WORKFLOW: cleanroom_wafer_cassette_loading.mp4 (No audio, ASR skipped, optical flow)
 */

import type {
  VideoMetadata,
  PipelineStageInfo,
  ProcessingLogEntry,
  WorkStep,
  ConflictItem,
  SOPDocument,
} from '../types/sop';

export interface WorkflowDataset {
  id: string;
  name: string;
  isSilent: boolean;
  video: VideoMetadata;
  stages: PipelineStageInfo[];
  logs: ProcessingLogEntry[];
  steps: WorkStep[];
  conflicts: ConflictItem[];
  document: SOPDocument;
}

// ---------------------------------------------------------------------------
// 1. Standard Demonstration With Audio (const_01.mp4 - Machine Operation)
// ---------------------------------------------------------------------------
export const STANDARD_AUDIO_WORKFLOW: WorkflowDataset = {
  id: 'wf_const_01_jp',
  name: 'Machine Operation and Maintenance (const_01.mp4)',
  isSilent: false,
  video: {
    filename: 'const_01.mp4',
    size_bytes: 91471350, // 91.47 MB
    duration_sec: 545.12, // 09:05 (545 sec)
    width: 1920,
    height: 1080,
    codec: 'h264',
    fps: 25.0,
    container_format: 'mov,mp4,m4a,3gp,3g2,mj2',
    audio_codec: 'aac',
    sample_rate: 48000,
    audio_channels: 2,
  },
  stages: [
    {
      key: 'video_intake',
      label: 'Video Intake',
      status: 'completed',
      description: 'Validate file & FFprobe container analysis',
      elapsed_sec: 8.0,
    },
    {
      key: 'audio_extraction',
      label: 'Audio Extraction',
      status: 'completed',
      description: 'Extract & standardize (16 kHz, mono, PCM)',
      elapsed_sec: 42.0,
    },
    {
      key: 'speech_transcription',
      label: 'Speech Transcription',
      status: 'processing',
      description: 'ASR (Speech to Text) - Faster-Whisper base (ja)',
      elapsed_sec: 80.0,
    },
    {
      key: 'step_detection',
      label: 'Work Step Detection',
      status: 'pending',
      description: 'Identify procedural steps from multimodal cues',
      elapsed_sec: 0,
    },
    {
      key: 'translation',
      label: 'Translation',
      status: 'pending',
      description: 'Generate bilingual SOP documentation (EN / JA)',
      elapsed_sec: 0,
    },
  ],
  logs: [
    {
      id: 'log_01',
      timestamp: '10:22:14',
      stage: 'Video Intake',
      message: 'File validation completed: 1920x1080 @ 25 fps (H.264), 91.47 MB',
      status: 'success',
    },
    {
      id: 'log_02',
      timestamp: '10:22:22',
      stage: 'Audio Extraction',
      message: 'Audio extracted (16 kHz, mono, PCM) from AAC stream (48 kHz stereo)',
      status: 'success',
    },
    {
      id: 'log_03',
      timestamp: '10:23:04',
      stage: 'Audio Extraction',
      message: 'Standardized WAV created (17.44 MB, EBU R128 normalized)',
      status: 'success',
    },
    {
      id: 'log_04',
      timestamp: '10:23:10',
      stage: 'Speech Transcription',
      message: 'ASR model loading (faster-whisper base, int8 CPU)',
      status: 'success',
    },
    {
      id: 'log_05',
      timestamp: '10:23:18',
      stage: 'Speech Transcription',
      message: 'Transcribing audio... (RTF: 0.23, Japanese confidence 0.9839)',
      status: 'processing',
    },
  ],
  steps: [
    {
      id: 'step_01',
      step_number: 1,
      title: 'Introduction',
      title_ja: 'はじめに',
      description: 'Overview of machine operation, pre-shift briefing, and procedural safety prerequisites.',
      description_ja: 'この動画では、機械の操作手順および作業前の安全確認事項について説明します。',
      start_time: 0.0,
      end_time: 80.0,
      keyframe_url: '/keyframes/const_step1.jpg',
      status: 'approved',
      tools_required: ['None (目視確認)'],
      ppe_required: ['Safety glasses (保護めがね)', 'Safety shoes (安全靴)'],
      safety_warnings: ['Ensure operator has completed factory certified machine handling course.'],
      quality_checkpoints: ['Check that emergency stop buttons are disengaged and accessible.'],
      expected_outcome: 'Operator is prepared and work area is confirmed operational.',
      evidence: [
        {
          id: 'ev_1_1',
          claim: 'Operator approaches control console',
          source: 'video',
          timestamp_sec: 10.0,
          observation: 'Operator checks main console screen status indicators',
        },
      ],
      reviewer_notes: 'Initial inspection protocol approved.',
    },
    {
      id: 'step_02',
      step_number: 2,
      title: 'Safety Check',
      title_ja: '安全確認',
      description: 'Check PPE equipment and ensure the work area is completely safe and clear of obstacles.',
      description_ja: '保護具を着用し、作業エリアおよび機械周辺が安全であることを確認します。',
      start_time: 15.0,
      end_time: 80.0,
      keyframe_url: '/keyframes/const_step2.jpg',
      status: 'approved',
      tools_required: ['None'],
      ppe_required: ['Safety gloves (保護手袋)', 'Safety shoes (安全靴)'],
      safety_warnings: [
        'Keep floor dry and clear of swarf or oil droplets.',
        '作業エリア内に障害物や油汚れがないことを確認してください。',
      ],
      quality_checkpoints: ['Perimeter interlock sensors active and green.'],
      expected_outcome: 'Machine environment certified safe for maintenance.',
      evidence: [
        {
          id: 'ev_2_1',
          claim: 'Verify safety zone boundary clearance',
          source: 'video',
          timestamp_sec: 35.0,
          observation: 'Operator inspects perimeter safety yellow line',
        },
      ],
      reviewer_notes: 'Safety check verified.',
    },
    {
      id: 'step_03',
      step_number: 3,
      title: 'Turn Off Main Switch',
      title_ja: '主電源を切る',
      description: 'Turn off the main power switch to stop the machine operation.',
      description_ja: '主電源を切り、機械の動作を停止します。',
      start_time: 80.0, // 01:20
      end_time: 155.0, // 02:35
      keyframe_url: '/keyframes/const_step3.jpg',
      status: 'approved',
      tools_required: ['None (使用する工具: なし)'],
      ppe_required: ['Safety gloves (recommended) (必要な保護具: 保護手袋 (推奨))'],
      safety_warnings: [
        'Ensure machine is in idle state before turning off main switch.',
        '主電源を切る前に、機械が停止状態であることを確認してください。',
      ],
      quality_checkpoints: [
        'Indicator lamp is OFF (インジケーターランプが消えていることを確認)',
        'No abnormal sounds (異常音がないことを確認)',
      ],
      expected_outcome: 'Machine power is completely turned off. (期待される結果: 機械の電源が完全に切れた状態。)',
      evidence: [
        {
          id: 'ev_3_1',
          claim: 'Locate main switch (主電源スイッチを確認)',
          source: 'video',
          timestamp_sec: 80.0, // 01:20
          observation: 'Operator locates main power rotary switch on console panel',
        },
        {
          id: 'ev_3_2',
          claim: 'Hand approaches switch (手をスイッチに近づける)',
          source: 'video',
          timestamp_sec: 95.0, // 01:35
          observation: 'Operator places hand firmly on rotary red switch knob',
        },
        {
          id: 'ev_3_3',
          claim: 'Turn switch to OFF (スイッチをOFFにする)',
          source: 'video',
          timestamp_sec: 105.0, // 01:45
          observation: 'Rotates switch 90 degrees counter-clockwise to OFF position',
        },
        {
          id: 'ev_3_4',
          claim: 'Indicator lamp turns off (インジケーターランプが消灯)',
          source: 'video',
          timestamp_sec: 130.0, // 02:10
          observation: 'Main power indicator LED on control panel turns completely dark',
        },
      ],
      reviewer_notes: 'Step verified and ready for expert review.',
    },
    {
      id: 'step_04',
      step_number: 4,
      title: 'Remove Safety Cover',
      title_ja: '安全カバーの取り外し',
      description: 'Remove the front safety cover by loosening the two screws.',
      description_ja: '前部の安全カバーを外し、2本のネジを緩めます。',
      start_time: 155.0, // 02:35
      end_time: 190.0, // 03:10
      keyframe_url: '/keyframes/const_step4.jpg',
      status: 'needs_review',
      tools_required: ['Screwdriver (Phillips) (十字ドライバー)', '5mm Hex Key (六角レンチ)'],
      ppe_required: ['Safety gloves (保護手袋)'],
      safety_warnings: [
        'Beware of pinch points behind retaining cover brackets.',
        '安全カバー裏側の突起部での挟まれに注意してください。',
      ],
      quality_checkpoints: ['Retain unfastened screws in magnetic tray.'],
      expected_outcome: 'Safety cover removed and internal mechanism visible.',
      evidence: [
        {
          id: 'ev_4_1',
          claim: 'Remove cover fasteners with hand tool',
          source: 'video',
          timestamp_sec: 165.0,
          observation: 'Operator unfastens front cover using Phillips screwdriver',
        },
      ],
      reviewer_notes: 'Conflict detected between video tool usage and reference manual specification.',
    },
    {
      id: 'step_05',
      step_number: 5,
      title: 'Check Components',
      title_ja: '部品の確認',
      description: 'Inspect exposed internal pulleys, timing belt, and mechanical guide ways for contamination.',
      description_ja: '露出した内部プーリー、タイミングベルト、ガイドウェイの汚れや摩耗を点検します。',
      start_time: 190.0, // 03:10
      end_time: 260.0, // 04:20
      keyframe_url: '/keyframes/const_step5.jpg',
      status: 'approved',
      tools_required: ['Inspection flashlight (点検用ライト)'],
      ppe_required: ['Safety glasses', 'Nitrile gloves'],
      safety_warnings: ['Do not touch moving parts or drive belts with bare fingers.'],
      quality_checkpoints: ['Belt deflection is within 3-5mm tolerance under thumb pressure.'],
      expected_outcome: 'Internal mechanisms verified clean and free of excessive backlash.',
      evidence: [
        {
          id: 'ev_5_1',
          claim: 'Visual inspection of drive belt tension',
          source: 'video',
          timestamp_sec: 215.0,
          observation: 'Operator shines light across drive belt teeth and checks tension',
        },
      ],
      reviewer_notes: 'Component check verified.',
    },
    {
      id: 'step_06',
      step_number: 6,
      title: 'Clean the Area',
      title_ja: '作業エリアの清掃',
      description: 'Clear chips and residual coolant residue from the housing pocket with lint-free wipes.',
      description_ja: 'ハウジング内部の切削粉や残留クーラントを不織布ワイパーで清掃します。',
      start_time: 260.0, // 04:20
      end_time: 305.0, // 05:05
      keyframe_url: '/keyframes/const_step6.jpg',
      status: 'pending',
      tools_required: ['Industrial vacuum', 'Lint-free wipes'],
      ppe_required: ['Safety glasses', 'Nitrile gloves'],
      safety_warnings: ['Never use compressed air inside closed bearing pockets.'],
      quality_checkpoints: ['No swarf particles remaining on guide surfaces.'],
      expected_outcome: 'Internal chamber thoroughly cleaned.',
      evidence: [],
    },
    {
      id: 'step_07',
      step_number: 7,
      title: 'Reassemble',
      title_ja: '再組み立て',
      description: 'Carefully reposition the protective cover and tighten mounting screws in diagonal sequence.',
      description_ja: '保護カバーを正確に位置決めし、固定ネジを対角線順に均等に締め付けます。',
      start_time: 305.0, // 05:05
      end_time: 375.0, // 06:15
      keyframe_url: '/keyframes/const_step7.jpg',
      status: 'pending',
      tools_required: ['Torque screwdriver (2.5 Nm)'],
      ppe_required: ['Safety gloves'],
      safety_warnings: ['Ensure wire harnesses are not pinched during cover reassembly.'],
      quality_checkpoints: ['Even perimeter gap around cover edge (< 0.5 mm).'],
      expected_outcome: 'Enclosure securely reinstalled.',
      evidence: [],
    },
    {
      id: 'step_08',
      step_number: 8,
      title: 'Power On',
      title_ja: '電源投入',
      description: 'Rotate main electrical disconnect switch back to the ON position and confirm boot cycle.',
      description_ja: '主電源スイッチをON位置に回し、システムの起動シーケンスを確認します。',
      start_time: 375.0, // 06:15
      end_time: 420.0, // 07:00
      keyframe_url: '/keyframes/const_step8.jpg',
      status: 'pending',
      tools_required: ['None'],
      ppe_required: ['Safety glasses'],
      safety_warnings: ['Clear all personnel away from moving axes before energizing.'],
      quality_checkpoints: ['CNC control screen boots with zero alarm codes.'],
      expected_outcome: 'System fully energized and servo drives ready.',
      evidence: [],
    },
    {
      id: 'step_09',
      step_number: 9,
      title: 'Verify Operation',
      title_ja: '動作確認',
      description: 'Initiate manual axis jog test and spindle rotation at 500 RPM to verify smooth operation.',
      description_ja: '各軸の手動送りおよび500 RPMでの主軸低速回転を実施し、動作を確認します。',
      start_time: 420.0, // 07:00
      end_time: 465.0, // 07:45
      keyframe_url: '/keyframes/const_step9.jpg',
      status: 'pending',
      tools_required: ['Handheld pendant controller'],
      ppe_required: ['Safety glasses'],
      safety_warnings: ['Keep feed override knob at 10% during initial jog.'],
      quality_checkpoints: ['Vibration levels below ISO 10816 threshold.'],
      expected_outcome: 'All mechanical axes operate within tolerance.',
      evidence: [],
    },
    {
      id: 'step_10',
      step_number: 10,
      title: 'Troubleshooting',
      title_ja: 'トラブルシューティング',
      description: 'Inspect acoustic feedback and bearing temperature using non-contact infrared thermometer.',
      description_ja: '放射温度計を用いてベアリング温度を測定し、異常過熱がないことを確認します。',
      start_time: 465.0, // 07:45
      end_time: 500.0, // 08:20
      keyframe_url: '/keyframes/const_step10.jpg',
      status: 'pending',
      tools_required: ['Infrared Thermometer'],
      ppe_required: ['Safety glasses'],
      safety_warnings: ['Report temperature rise exceeding 15°C above ambient.'],
      quality_checkpoints: ['Spindle nose temperature steady at < 45°C.'],
      expected_outcome: 'Thermal and acoustic diagnostics confirmed nominal.',
      evidence: [],
    },
    {
      id: 'step_11',
      step_number: 11,
      title: 'Maintenance Notes',
      title_ja: '保守記録の作成',
      description: 'Fill in the digital work order log with inspection date, technician initials, and findings.',
      description_ja: '点検実施日、作業者名、測定値をデジタル保守点検台帳に記録します。',
      start_time: 500.0, // 08:20
      end_time: 530.0, // 08:50
      keyframe_url: '/keyframes/const_step11.jpg',
      status: 'pending',
      tools_required: ['Maintenance tablet terminal'],
      ppe_required: ['None'],
      safety_warnings: ['Ensure accurate timestamping for compliance tracking.'],
      quality_checkpoints: ['All required log fields completed and saved.'],
      expected_outcome: 'Full digital audit trail stored in facility MES.',
      evidence: [],
    },
    {
      id: 'step_12',
      step_number: 12,
      title: 'Completion',
      title_ja: '作業完了',
      description: 'Release lockout tag, return tools to 5S shadow board, and release machine to production.',
      description_ja: '工具を定位置に戻し、機械を生産稼働可能状態として引き渡します。',
      start_time: 530.0, // 08:50
      end_time: 545.12, // 09:05
      keyframe_url: '/keyframes/const_step12.jpg',
      status: 'pending',
      tools_required: ['None'],
      ppe_required: ['Safety glasses'],
      safety_warnings: ['Confirm area 5S housekeeping check completed.'],
      quality_checkpoints: ['Work instruction sign-off counter signed by team lead.'],
      expected_outcome: 'Machine released for scheduled production run.',
      evidence: [],
    },
  ],
  conflicts: [
    {
      id: 'conf_step_04',
      step_id: 'step_04',
      step_number: 4,
      step_title: 'Remove Safety Cover (安全カバーの取り外し)',
      video_evidence: {
        keyframe_url: '/keyframes/const_step4.jpg',
        timestamp_sec: 165.0, // 02:35 - 03:10
        observed_action: 'Remove the front safety cover by loosening the two screws. (前部の安全カバーを外し、2本のネジを緩めます。)',
        detected_tools: ['Screwdriver (Phillips)', 'None (other)'],
      },
      reference_manual: {
        document_name: 'Machine Operation & Maintenance Manual Rev 2.1',
        page_number: 14,
        relevant_instruction: 'Remove the top safety cover using a 5mm hex key. (上部の安全カバーを外し、5mmの六角レンチを使用して固定具を取り外します。)',
        required_tools: ['5mm Hex Key', 'Safety gloves'],
      },
      difference: 'Different cover location: Video shows front cover, manual shows top cover. Different tools: Video shows screwdriver, manual requires 5mm hex key.',
      resolved: false,
    },
  ],
  document: {
    id: 'sop_doc_const_01',
    title: 'Standard Operating Procedure (SOP) / 標準作業手順書',
    title_ja: '機械の操作およびメンテナンス (Machine Operation and Maintenance)',
    version: '1.0',
    approved_by: 'ET Engineering Team',
    approved_date: '10/09/2026 14:32',
    all_approved: false,
    steps: [],
    audit_trail: [
      {
        id: 'aud_01',
        timestamp: '10/09/2026 10:15',
        actor: 'system',
        action: 'Ingested video file const_01.mp4 (91.47 MB, 09:05)',
        stage: 'Video Intake',
        status: 'completed',
      },
      {
        id: 'aud_02',
        timestamp: '10/09/2026 10:18',
        actor: 'system',
        action: 'Extracted 16 kHz mono WAV (17.44 MB) via FFmpeg audio pipeline',
        stage: 'Audio Extraction',
        status: 'completed',
      },
      {
        id: 'aud_03',
        timestamp: '10/09/2026 10:22',
        actor: 'faster-whisper',
        action: 'Speech transcription started: Japanese (ja) detected with 0.9839 confidence',
        stage: 'Speech Transcription',
        status: 'completed',
      },
      {
        id: 'aud_04',
        timestamp: '10/09/2026 10:25',
        actor: 'system',
        action: 'Identified 12 procedural steps with 1 flagged discrepancy against Rev 2.1 manual',
        stage: 'Work Step Detection',
        status: 'completed',
      },
    ],
  },
};

// ---------------------------------------------------------------------------
// 2. Silent Demonstration (Cleanroom Wafer Cassette Loading - No Audio)
// ---------------------------------------------------------------------------
export const SILENT_INSPECTION_WORKFLOW: WorkflowDataset = {
  id: 'wf_cleanroom_002',
  name: 'Cleanroom FOUP Wafer Cassette Loading (Silent Video)',
  isSilent: true,
  video: {
    filename: 'cleanroom_wafer_cassette_loading.mp4',
    size_bytes: 52428800, // 50.0 MB
    duration_sec: 180.0, // 03:00
    width: 1920,
    height: 1080,
    codec: 'h264',
    fps: 30.0,
    container_format: 'mov,mp4,m4a,3gp,3g2,mj2',
    audio_codec: null, // STRICT NULL: Cleanroom recordings contain no microphone audio
    sample_rate: null,
    audio_channels: null,
  },
  stages: [
    {
      key: 'video_intake',
      label: 'Video Intake',
      status: 'completed',
      description: 'FFprobe container inspection confirmed 1920x1080 @ 30 FPS',
      elapsed_sec: 1.1,
    },
    {
      key: 'audio_extraction',
      label: 'Audio Extraction',
      status: 'skipped',
      description: 'Container contains no audio stream; audio extraction skipped',
      elapsed_sec: 0,
    },
    {
      key: 'speech_transcription',
      label: 'Speech Transcription',
      status: 'skipped',
      description: 'No audio track present in file; ASR automatically bypassed',
      elapsed_sec: 0,
    },
    {
      key: 'step_detection',
      label: 'Work-Step Detection',
      status: 'completed',
      description: '3 work steps identified using visual optical flow and motion bounding boxes',
      elapsed_sec: 7.2,
    },
    {
      key: 'translation',
      label: 'Translation',
      status: 'completed',
      description: 'Standardized semiconductor cleanroom terminology aligned (EN / JA)',
      elapsed_sec: 3.4,
    },
  ],
  logs: [
    {
      id: 'slog_01',
      timestamp: '11:05:02',
      stage: 'Video Intake',
      message: 'Container validated: cleanroom_wafer_cassette_loading.mp4 (50.0 MB, H.264)',
      status: 'success',
    },
    {
      id: 'slog_02',
      timestamp: '11:05:03',
      stage: 'Audio Extraction',
      message: 'FFprobe returned no audio stream (audio_codec == null). Audio extraction skipped',
      status: 'warning',
    },
    {
      id: 'slog_03',
      timestamp: '11:05:03',
      stage: 'Speech Transcription',
      message: 'ASR bypassed: silent video demonstration. Visual evidence grounding primary',
      status: 'warning',
    },
    {
      id: 'slog_04',
      timestamp: '11:05:14',
      stage: 'Work-Step Detection',
      message: 'Segmented 3 visual work steps from keyframe optical flow analysis',
      status: 'success',
    },
  ],
  steps: [
    {
      id: 'sstep_01',
      step_number: 1,
      title: 'Position FOUP Cassette on Load Port',
      title_ja: 'FOUPカセットをロードポートへ正確に載置する',
      description: 'Align FOUP cassette bottom kinematic pins with the load port docking receiver.',
      description_ja: 'FOUPカセット底面のキネマティックピンをロードポートの位置決め穴に確実に位置合わせして載置します。',
      start_time: 0.0,
      end_time: 55.0,
      keyframe_url: '/keyframes/cleanroom_step1.jpg',
      status: 'approved',
      tools_required: ['Cleanroom pneumatic ergonomic lift assist'],
      ppe_required: ['Class 100 cleanroom bunny suit', 'Nitrile cleanroom gloves'],
      safety_warnings: ['Ensure cassette is lowered smoothly without shock load to wafer carrier.'],
      quality_checkpoints: ['Kinematic coupling indicators illuminate solid green on port console.'],
      expected_outcome: 'Cassette securely docked with zero particulate generation.',
      evidence: [
        {
          id: 'sev_1_1',
          claim: 'Cassette lowered onto kinematic pin receivers',
          source: 'video',
          timestamp_sec: 38.0,
          observation: 'Operator aligns front bezel markers with docking plate',
        },
      ],
      reviewer_notes: 'Visual alignment procedure verified.',
    },
    {
      id: 'sstep_02',
      step_number: 2,
      title: 'Engage Automated Door Latch Release',
      title_ja: '自動ドアラッチ解除機構の作動',
      description: 'Activate load port vacuum seal mechanism and verify twin latch keys rotate 90 degrees.',
      description_ja: 'ロードポートの真空シール機構を作動させ、2基のラッチキーが90度回転して解錠されたことを確認します。',
      start_time: 55.0,
      end_time: 110.0,
      keyframe_url: '/keyframes/cleanroom_step2.jpg',
      status: 'approved',
      tools_required: ['Automated load port controller'],
      ppe_required: ['Full cleanroom suit', 'Nitrile cleanroom gloves'],
      safety_warnings: ['Keep hands clear of the descending port door mechanism.'],
      quality_checkpoints: ['Vacuum differential gauge indicates delta-P < 5 Pa.'],
      expected_outcome: 'Cassette door opened and wafers accessible to cleanroom robot arm.',
      evidence: [
        {
          id: 'sev_2_1',
          claim: 'Door lowers into sub-chassis chamber',
          source: 'video',
          timestamp_sec: 92.0,
          observation: 'FOUP door drawn into lower housing revealing wafer rack',
        },
      ],
      reviewer_notes: 'Port latch sequence verified.',
    },
    {
      id: 'sstep_03',
      step_number: 3,
      title: 'Optical Wafer Cross-Slot Scan Verification',
      title_ja: '光学式クロススロット検出によるウェハ積載確認',
      description: 'Observe mapping sensor array sweep across 25 wafer slot positions. Confirm zero tilted wafers.',
      description_ja: 'マッピングセンサーが25段のスロット位置を走査し、斜め挿入（クロススロット）のないことを確認します。',
      start_time: 110.0,
      end_time: 180.0,
      keyframe_url: '/keyframes/cleanroom_step3.jpg',
      status: 'approved',
      tools_required: ['Load port optical mapping sensor'],
      ppe_required: ['Full cleanroom suit', 'Safety glasses'],
      safety_warnings: ['Do not interrupt optical scan beam with external objects.'],
      quality_checkpoints: ['Map scan registers 25/25 slots occupied with zero wafer slope error.'],
      expected_outcome: 'All 25 silicon wafers verified properly seated in horizontal slots.',
      evidence: [
        {
          id: 'sev_3_1',
          claim: 'Optical sensor bar passes through wafer cassette edge',
          source: 'video',
          timestamp_sec: 125.0,
          observation: 'Red optical scan line travels from bottom slot 1 to top slot 25',
        },
      ],
      reviewer_notes: 'Optical wafer scan verified.',
    },
  ],
  conflicts: [],
  document: {
    id: 'sop_doc_wafer_002',
    title: 'Standard Operating Procedure: Cleanroom FOUP Cassette Loading',
    title_ja: '標準作業手順書：クリーンルームFOUPカセットローディング手順',
    version: 'Rev 1.0',
    approved_by: 'Process Engineering Group',
    approved_date: '2026-09-10',
    all_approved: true,
    steps: [],
    audit_trail: [
      {
        id: 'saud_01',
        timestamp: '2026-09-10 11:05:02',
        stage: 'Video Ingestion',
        actor: 'system',
        action: 'Ingested silent demonstration video cleanroom_wafer_cassette_loading.mp4 (50.0 MB)',
        status: 'completed',
      },
      {
        id: 'saud_02',
        timestamp: '2026-09-10 11:05:03',
        stage: 'Audio Processing',
        actor: 'system',
        action: 'Container audio stream probe: none. ASR skipped (no audio stream)',
        status: 'skipped',
      },
      {
        id: 'saud_03',
        timestamp: '2026-09-10 11:05:14',
        stage: 'Visual Step Detection',
        actor: 'system',
        action: 'Segmented 3 visual work steps from keyframe optical flow analysis',
        status: 'completed',
      },
    ],
  },
};
