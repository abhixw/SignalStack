import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Briefcase, ChevronRight, CheckCircle } from 'lucide-react';
import { getCandidateJobs, getCandidateApplications } from '../api';
import { useAuth } from '../context/AuthContext';
import { JOB_ROLES } from '../constants';

export default function CandidateJobs() {
    const [jobs, setJobs] = useState([]);
    const [appliedJobIds, setAppliedJobIds] = useState(new Set());
    const [loading, setLoading] = useState(true);
    const [jobRole, setJobRole] = useState('');
    const { user } = useAuth();

    useEffect(() => {
        // Public endpoint — candidates can browse before signing in.
        async function loadJobs() {
            setLoading(true);
            try {
                const [jobsData, applications] = await Promise.all([
                    getCandidateJobs({ jobRole: jobRole || undefined }),
                    user?.role === 'candidate' ? getCandidateApplications().catch(() => []) : Promise.resolve([]),
                ]);
                setJobs(jobsData);
                setAppliedJobIds(new Set(applications.map((a) => a.job_id)));
            } catch (error) {
                console.error("Failed to load jobs", error);
            } finally {
                setLoading(false);
            }
        }
        loadJobs();
    }, [user, jobRole]);

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Available Job Postings</h1>
                    <p className="mt-1 text-sm text-gray-500">
                        {user ? (
                            <>Welcome, <span className="font-semibold text-indigo-600">{user.email}</span>. Browse and apply to active roles.</>
                        ) : (
                            <>Browse active roles. <Link to="/login" className="text-indigo-600 font-medium hover:text-indigo-500">Sign in</Link> to apply.</>
                        )}
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <select
                        value={jobRole}
                        onChange={(e) => setJobRole(e.target.value)}
                        className="rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm py-2 pl-3 pr-8 border bg-white"
                    >
                        <option value="">All roles</option>
                        {JOB_ROLES.map((role) => (
                            <option key={role} value={role}>{role}</option>
                        ))}
                    </select>
                    {user?.role === 'candidate' && (
                        <Link
                            to="/candidate/applications"
                            className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                        >
                            My Applications
                        </Link>
                    )}
                </div>
            </div>

            {loading ? (
                <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent"></div>
                    <p className="mt-2 text-gray-500">Loading jobs...</p>
                </div>
            ) : jobs.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-gray-300">
                    <Briefcase className="mx-auto h-12 w-12 text-gray-400" />
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No active job postings</h3>
                    <p className="mt-1 text-sm text-gray-500">Check back later for new opportunities.</p>
                </div>
            ) : (
                <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                    {jobs.map((job) => {
                        const applied = appliedJobIds.has(job.id);
                        return (
                            <div key={job.id} className="bg-white overflow-hidden shadow rounded-lg border border-gray-200 flex flex-col">
                                <div className="px-4 py-5 sm:p-6 flex-grow">
                                    <div className="flex items-center justify-between mb-4">
                                        <div className="flex items-center">
                                            <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center">
                                                <Briefcase className="h-5 w-5 text-indigo-600" />
                                            </div>
                                            <div className="ml-3">
                                                <h3 className="text-lg font-medium text-gray-900">{job.title}</h3>
                                            </div>
                                        </div>
                                        {applied && (
                                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                <CheckCircle className="h-3 w-3" />
                                                Applied
                                            </span>
                                        )}
                                    </div>
                                    {job.job_role && (
                                        <span className="inline-block mb-2 px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                                            {job.job_role}
                                        </span>
                                    )}
                                    <p className="text-sm text-gray-500 line-clamp-3 mb-4">{job.description}</p>
                                    <div className="flex flex-wrap gap-2">
                                        {job.tasks.map((task, index) => (
                                            <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                                {task.title}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                                <div className="bg-gray-50 px-4 py-4 sm:px-6">
                                    {applied ? (
                                        <Link
                                            to="/candidate/applications"
                                            className="w-full inline-flex justify-center items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-600 bg-white hover:bg-gray-50 transition-colors"
                                        >
                                            View Application
                                        </Link>
                                    ) : (
                                        <Link
                                            to={`/submit-proof/${job.id}`}
                                            className="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 transition-colors"
                                        >
                                            Apply Now
                                            <ChevronRight className="ml-1 h-4 w-4" />
                                        </Link>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
