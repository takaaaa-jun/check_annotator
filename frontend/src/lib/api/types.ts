export type ErrorDetail = {
  code: string;
  message: string;
};

export type APIErrorResponse = {
  detail: ErrorDetail;
};

export type LoginResponse = {
  user: {
    user_id: number;
    user_name: string;
    role_name: string;
  };
};

export type CurrentUser = {
  user_id: number;
  user_name: string;
  role_id: number;
  role_name: string;
  login_at: string | null;
};

export type StateCount = {
  state_id: number;
  state_name: string;
  count: number;
};

export type GroupProgress = {
  group_id: number;
  group_name: string;
  image_id_min: number | null;
  image_id_max: number | null;
  total_count: number;
  state_counts: StateCount[];
};

export type UserGroupsResponse = {
  user: {
    user_id: number;
    user_name: string;
  };
  groups: GroupProgress[];
};

export type Task = {
  task_id: number;
  image_id: number;
  state_id: number;
  state_name: string;
  updated_at: string;
};

export type Pagination = {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type GroupTasksResponse = {
  group: {
    group_id: number;
    group_name: string;
    user_id: number;
    user_name: string;
  };
  tasks: Task[];
  pagination: Pagination;
};

export type TaskStateResponse = Task & {
  group_id: number | null;
};

export type Comment = {
  comment_id: number;
  user_id: number;
  user_name: string;
  parent_id: number | null;
  content: string;
  created_at: string;
  updated_at: string;
};

export type CreatedComment = Comment & {
  task_id: number;
};

export type TaskCommentsResponse = {
  task_id: number;
  comments: Comment[];
  pagination: Pagination;
};