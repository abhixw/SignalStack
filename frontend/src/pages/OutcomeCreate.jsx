import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, Save, Sparkles } from 'lucide-react';
import { createOutcome, suggestTasks } from '../api';

export default function OutcomeCreate() {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        id: '',
        title: '',
        description: '',
        tasks: [
            { task_id: 't1', title: '', success_criteria: { outcome: '' }, importance: 'High' }
        ],
        rubric: { reliability: 0.4, technical_depth: 0.4, completeness: 0.2 }
    });

    const addTask = () => {
        const newId = `task-${Date.now()}`;
        setFormData({
            ...formData,
            tasks: [...formData.tasks, { task_id: newId, title: '', success_criteria: { outcome: '' }, importance: 'Medium' }]
        });
    };

    const removeTask = (index) => {
        const newTasks = [...formData.tasks];
        newTasks.splice(index, 1);
        setFormData({ ...formData, tasks: newTasks });
    };

    const updateTask = (index, field, value) => {
        const newTasks = [...formData.tasks];
        if (field === 'outcome') {
            newTasks[index].success_criteria.outcome = value;
        } else {
            newTasks[index][field] = value;
        }
        setFormData({ ...formData, tasks: newTasks });
    };

    const handleSuggestTasks = async () => {
        if (!formData.description) return;
        setLoading(true);
        try {
            const suggestions = await suggestTasks(formData.description);
            if (suggestions && suggestions.length > 0) {
                const timestamp = Date.now();
                const newTasks = suggestions.map((s, i) => ({
                    task_id: `task-${timestamp}-${i}`,
                    title: s.title,
                    success_criteria: { outcome: s.outcome },
                    importance: s.importance
                }));
                setFormData({ ...formData, tasks: newTasks });
            }
        } catch (error) {
            console.error("Failed to suggest tasks", error);
            alert("Failed to generate tasks. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            // Auto-generate ID if empty
            const payload = { ...formData };
            if (!payload.id) {
                payload.id = payload.title.toLowerCase().replace(/[^a-z0-9]+/g, '-');
            }
            await createOutcome(payload);
            navigate(`/dashboard/${payload.id}`);
        } catch (error) {
            console.error("Failed to create outcome", error);
            alert(`Error: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold text-gray-900">Define Outcome</h1>
                <button
                    onClick={handleSubmit}
                    disabled={loading}
                    className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                >
                    <Save className="w-5 h-5 mr-2" />
                    {loading ? 'Saving...' : 'Save Outcome'}
                </button>
            </div>

            <div className="bg-white shadow-sm rounded-xl p-8 border border-gray-100 space-y-6">
                <h2 className="text-xl font-semibold text-gray-900 border-b pb-2">1. Outcome Definition</h2>
                <div className="grid grid-cols-1 gap-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Outcome Title</label>
                        <input
                            type="text"
                            placeholder="e.g. Build Payments API v1"
                            value={formData.title}
                            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3 border"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Description</label>
                        <textarea
                            rows={3}
                            placeholder="Describe the high-level goal..."
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-3 border"
                        />
                    </div>
                </div>
            </div>

            <div className="bg-white shadow-sm rounded-xl p-8 border border-gray-100 space-y-6">
                <div className="flex justify-between items-center border-b pb-2">
                    <h2 className="text-xl font-semibold text-gray-900">2. Task Decomposition (Critical)</h2>
                    <div className="flex gap-2">
                        <button
                            type="button"
                            onClick={handleSuggestTasks}
                            disabled={loading || !formData.description}
                            className="inline-flex items-center px-3 py-1.5 border border-indigo-200 text-xs font-medium rounded-md text-indigo-700 bg-indigo-50 hover:bg-indigo-100 disabled:opacity-50"
                        >
                            <Sparkles className="w-4 h-4 mr-1" />
                            Suggest with AI
                        </button>
                        <button
                            type="button"
                            onClick={addTask}
                            className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200"
                        >
                            <Plus className="w-4 h-4 mr-1" />
                            Add Task
                        </button>
                    </div>
                </div>

                <div className="space-y-4">
                    {formData.tasks.map((task, index) => (
                        <div key={task.task_id} className="bg-gray-50 p-4 rounded-lg border border-gray-200 relative">
                            <button
                                type="button"
                                onClick={() => removeTask(index)}
                                className="absolute top-4 right-4 text-gray-400 hover:text-red-500"
                            >
                                <Trash2 className="w-5 h-5" />
                            </button>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pr-8">
                                <div>
                                    <label className="block text-xs font-medium text-gray-500 uppercase">Task Name</label>
                                    <input
                                        type="text"
                                        placeholder="e.g. Rate limiting"
                                        value={task.title}
                                        onChange={(e) => updateTask(index, 'title', e.target.value)}
                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-500 uppercase">Importance</label>
                                    <select
                                        value={task.importance}
                                        onChange={(e) => updateTask(index, 'importance', e.target.value)}
                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                    >
                                        <option>Low</option>
                                        <option>Medium</option>
                                        <option>High</option>
                                    </select>
                                </div>
                                <div className="md:col-span-2">
                                    <label className="block text-xs font-medium text-gray-500 uppercase">Task Outcome Description</label>
                                    <input
                                        type="text"
                                        placeholder="e.g. Sustain 50k RPM without failures"
                                        value={task.success_criteria.outcome}
                                        onChange={(e) => updateTask(index, 'outcome', e.target.value)}
                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                                    />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="bg-white shadow-sm rounded-xl p-8 border border-gray-100 space-y-6">
                <h2 className="text-xl font-semibold text-gray-900 border-b pb-2">3. Constraints & Bias (Optional)</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {Object.entries(formData.rubric).map(([key, val]) => (
                        <div key={key}>
                            <label className="block text-sm font-medium text-gray-700 capitalize">{key.replace('_', ' ')} Weight</label>
                            <input
                                type="number"
                                step="0.1"
                                min="0"
                                max="1"
                                value={val}
                                onChange={(e) => setFormData({
                                    ...formData,
                                    rubric: { ...formData.rubric, [key]: parseFloat(e.target.value) }
                                })}
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                            />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
