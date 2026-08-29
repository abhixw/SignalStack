import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Clock, AlertCircle, ArrowLeft, ThumbsUp, ThumbsDown, Search } from 'lucide-react';
import { getCandidateApplications } from '../api';

const STATUS_STYLES = {
    'Advancing to Interview': { icon: ThumbsUp, badge: 'bg-green-100 text-green-800', iconBg: 'bg-green-100', iconColor: 'text-green-600' },
    'Rejected': { icon: ThumbsDown, badge: 'bg-red-100 text-red-800', iconBg: 'bg-red-100', iconColor: 'text-red-600' },
    'Under Review': { icon: Search, badge: 'bg-blue-100 text-blue-800', iconBg: 'bg-blue-100', iconColor: 'text-blue-600' },
    'Pending': { icon: Clock, badge: 'bg-yellow-100 text-yellow-800', iconBg: 'bg-yellow-100', iconColor: 'text-yellow-600' },
};

export default function CandidateApplications() {
    const [applications, setApplications] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Identity is derived from the logged-in candidate's JWT — the backend
        // never accepts a client-supplied candidate id here.
        async function loadApplications() {
            try {
                const data = await getCandidateApplications();
                setApplications(data);
            } catch (error) {
                console.error("Failed to load applications", error);
            } finally {
                setLoading(false);
            }
        }
        loadApplications();
    }, []);

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="mb-8 flex items-center">
                <Link to="/candidate/jobs" className="mr-4 p-2 rounded-full hover:bg-gray-100 transition-colors">
                    <ArrowLeft className="h-6 w-6 text-gray-500" />
                </Link>
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">My Applications</h1>
                    <p className="mt-1 text-sm text-gray-500">Track your progress and view evaluation results.</p>
                </div>
            </div>

            {loading ? (
                <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent"></div>
                    <p className="mt-2 text-gray-500">Loading your applications...</p>
                </div>
            ) : applications.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-gray-300">
                    <FileText className="mx-auto h-12 w-12 text-gray-400" />
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No applications yet</h3>
                    <p className="mt-1 text-sm text-gray-500">You haven't applied to any jobs. Go to the jobs list to get started!</p>
                    <div className="mt-6">
                        <Link
                            to="/candidate/jobs"
                            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                        >
                            Browse Jobs
                        </Link>
                    </div>
                </div>
            ) : (
                <div className="bg-white shadow overflow-hidden sm:rounded-md border border-gray-200">
                    <ul className="divide-y divide-gray-200">
                        {applications.map((app, index) => {
                            const style = STATUS_STYLES[app.status] || STATUS_STYLES['Pending'];
                            const StatusIcon = style.icon;
                            return (
                                <li key={index} className="px-4 py-6 sm:px-6">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center">
                                            <div className={`h-12 w-12 rounded-lg flex items-center justify-center mr-4 ${style.iconBg}`}>
                                                <StatusIcon className={`h-6 w-6 ${style.iconColor}`} />
                                            </div>
                                            <div>
                                                <h3 className="text-lg font-medium text-gray-900">{app.job_title}</h3>
                                                <div className="flex items-center mt-1 text-sm text-gray-500">
                                                    <span>Applied on: {new Date(app.applied_at).toLocaleDateString()}</span>
                                                </div>
                                            </div>
                                        </div>

                                        <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold ${style.badge}`}>
                                            <StatusIcon className="h-4 w-4" />
                                            {app.status}
                                        </span>
                                    </div>

                                    {app.status === 'Pending' && (
                                        <div className="mt-4 p-4 bg-gray-50 rounded-md border border-gray-100">
                                            <div className="flex">
                                                <AlertCircle className="h-5 w-5 text-gray-400 mr-2" />
                                                <p className="text-sm text-gray-600">Your application is in queue. The recruiter will trigger the AI evaluation soon.</p>
                                            </div>
                                        </div>
                                    )}
                                    {app.status === 'Under Review' && (
                                        <div className="mt-4 p-4 bg-gray-50 rounded-md border border-gray-100">
                                            <div className="flex">
                                                <FileText className="h-5 w-5 text-gray-400 mr-2" />
                                                <p className="text-sm text-gray-600">Your work has been evaluated. The recruiter hasn't made a decision yet — check back later.</p>
                                            </div>
                                        </div>
                                    )}
                                    {app.feedback && (
                                        <div className="mt-4 p-4 bg-indigo-50 rounded-md border border-indigo-100">
                                            <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide mb-1">Feedback from the recruiter</p>
                                            <p className="text-sm text-gray-700 whitespace-pre-wrap">{app.feedback}</p>
                                        </div>
                                    )}
                                </li>
                            );
                        })}
                    </ul>
                </div>
            )}
        </div>
    );
}
